#!/usr/bin/env python
# -*- coding: utf-8 -*-
from argparse import ArgumentParser
from datetime import datetime
from hashlib import sha1
import requests
import json
import os

CURRENT_PATH = os.getcwd().replace("\\", "/")

if os.name == "nt":
    CONFIG_PATH = '/'.join((os.environ["ProgramData"].replace("\\", "/"), "nexus-manager"))
elif os.name == "posix":
    CONFIG_PATH = f"/Users/{os.getlogin()}/Library/Preferences"
else:
    CONFIG_PATH = "/etc/nexus-manager"

CONFIG_DATA = {
    "AUTH": "",
    "SERVER_URI": "http://localhost:8081"
}

if not os.path.exists(CONFIG_PATH):
    os.mkdir(CONFIG_PATH)

if not os.path.isfile(f"{CONFIG_PATH}/config.json"):
    with open(f"{CONFIG_PATH}/config.json", "w") as f:
        json.dump(CONFIG_DATA, f)
else:
    with open(f"{CONFIG_PATH}/config.json", "r") as f:
        CONFIG_DATA = json.load(f)
        
from private import USER, PASSWORD

def log(*args) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]", end=" ")
    for arg in args:
        print(arg, end=" ")
    print(end="\n")

def update_config(key: str, value: str) -> None:
    CONFIG_DATA[key] = value
    with open(f"{CONFIG_PATH}/config.json", "w") as f:
        json.dump(CONFIG_DATA, f)

def print_config() -> None:
    print(f"Auth: {CONFIG_DATA['AUTH']}\nServer URI: {CONFIG_DATA['SERVER_URI']}")

class NexusRawDownload():
    def __init__(self, user: str, password: str, filter_options: tuple, config_path: str = CURRENT_PATH, force_download: bool = False) -> None:
        if config_path.endswith("/"): config_path = config_path[:-1]
        self.auth = (user, password)
        self.config_path = config_path
        self.force_download = force_download
        self.filter = filter_options
        self.tasks = self._parse_config()
        self._check_server()

    # Parses config file at initialisation
    def _parse_config(self) -> list:
        tasks = []
        if not os.path.isfile(f"{self.config_path}/external.config"):
            raise FileNotFoundError(f"Config file not found")
        with open(f"{self.config_path}/external.config", "r") as f:
            for line in f.readlines():
                line = line.strip().split("#")[0]
                if len(line) == 0:
                    continue
                line = line.split()
                tasks.append((line[0], line[1]))
        return tasks
    
    # Checks if server is up
    def _check_server(self) -> None:
        try:
            r = requests.get(CONFIG_DATA['SERVER_URI'], auth=self.auth)
            if not r.ok:
                raise ConnectionRefusedError(f"Server {CONFIG_DATA['SERVER_URI']} check failed")
        except:
            raise ConnectionRefusedError(f"Server {CONFIG_DATA['SERVER_URI']} check failed")
    
    # Parses all dirs recursively
    def _parse_dirs(self, path: str, all_paths: list[str]) -> None:
        for p in os.scandir(path):
            if p.is_dir():
                all_paths.append(p.path)
                self._parse_dirs(p, all_paths)

    # Parses all dirs, then self.start for dirs w/ correct config file
    def start_recursive(self) -> None:
        current_paths = [self.config_path]
        self._parse_dirs(self.config_path, current_paths)
        for path in current_paths:
            try:
                self.config_path = path
                self.tasks = self._parse_config()
            except FileNotFoundError:
                log(f"Not found/Wrong config file in {path}")
                continue
            self.start()

    # Downloads projects one by one
    def start(self) -> None:
        for task in self.tasks:
            self._start_task(task[0], task[1])

    # Download project function
    def _start_task(self, project_name: str, version: str) -> None:
        rep_components = self._get_rep(project_name)
        flag = False
        log(f"Downloading {project_name}-{version}...")
        for comp in rep_components:
            if comp[0].startswith(f"{project_name}-{version}") and comp[0].split("/")[-1] == ".metadata":
                self._handle_metadata(project_name, comp[0])
                flag = True
            elif comp[0].startswith(f"{project_name}-{version}") and self._filter(comp[0].split("/")[2].split("-")):
                self._handle_component(project_name, comp[0], comp[1], self.force_download)
                flag = True
        if flag:
            log(f"Successfully downloaded {project_name}-{version}")
        else:
            log(f"Nothing to download for {project_name}-{version}")

            
    # Get repository components
    def _get_rep(self, rep_name: str) -> list:
        r = requests.get(f"{CONFIG_DATA['SERVER_URI']}/service/rest/v1/components?repository={rep_name}", auth=self.auth)
        if r.ok:
            return [(item["name"], item["assets"][0]["checksum"]["sha1"]) for item in r.json()["items"]]
        return []
    
    # Filter components by platform/architecture/target
    def _filter(self, filter: list) -> bool:
        for _ in range(3):
            if len(self.filter[_]) != 0 and self.filter[_] != filter[_]:
                return False
        return True

    # Generate path to given component
    def _generate_filepath(self, component: str) -> str:
        return '/'.join((self.config_path, "external", '/'.join(component.split('/')[1:])))

    # Handle component: generate downloaded file path -> make dirs -> download
    def _handle_component(self, project_name: str, component: str, checksum: str, force_download: bool = False) -> None:
        filepath = self._generate_filepath(component)
        filedir = f"{self.config_path}/external/{'/'.join(component.split('/')[1:-1])}"
        if not os.path.exists(filedir):
            os.makedirs(filedir)
        if force_download or not os.path.isfile(filepath) or (os.path.isfile(filepath) and sha1(open(filepath,'rb').read()).hexdigest() != checksum):
            self._send_download_request(filepath, f"{project_name}/{component}")
    
    # Handle metadata file:
    def _handle_metadata(self, project_name: str, component: str):
        filepath = self._generate_filepath(component)
        self._send_download_request(filepath, f"{project_name}/{component}", False)
        with open(filepath, "r") as metadata:
            metadata = metadata.readlines()
            self._parse_metadata(metadata, project_name)
        os.remove(filepath)

    # Parses metadata and creates symlinks
    def _parse_metadata(self, data: list, project_name: str) -> None:
        current_parent = 0
        for line in data:
            line = line.strip().split()
            if line[0] == "symlinks:":
                current_parent = 1
            else:
                if current_parent == 1:
                    symlink_path = f"{self.config_path}/external/{project_name}/{line[0]}"
                    symlink_path_to = self._get_target_path(line[0], line[1], project_name)
                    if symlink_path_to == None:
                        log(f"[!] Symlink {line[0]} target out of range; Skipped")
                        continue
                    try:
                        os.symlink(symlink_path_to, symlink_path)
                        log(f"Saved symlink to {symlink_path}")
                    except:
                        pass

    # Gets target path
    # if absolute -> checks if link to file/dir inside {project_name} dir
    # if relative -> checks if steps back count < available steps back for symlink path
    def _get_target_path(self, symlink_path: str, target: str, project_name: str) -> str | None:
        if os.path.isabs(target):
            if len(target.split(project_name)) == 1:
                return None
            return f"{self.config_path}/external/{project_name}/{target.split(project_name)[1]}"
        steps_count = len(symlink_path.split("/")) - 1
        steps_back_count = 0
        for part in target.split("/"):
            if part == "..":
                steps_back_count +=1
        if steps_back_count > steps_count:
            return None
        return target

    # Downloads component from rep to given path
    def _send_download_request(self, download_to_path: str, endpoint: str, not_silent: bool = True) -> None:
        r = requests.get(f"{CONFIG_DATA['SERVER_URI']}/repository/{endpoint}", stream=True, auth=self.auth)
        if r.ok:
            if not_silent: log("Saving component to", download_to_path)
            with open(download_to_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 8):
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        os.fsync(f.fileno())
            return
        if not_silent: log(f"Download failed: Status code {r.status_code}\n{download_to_path}\n{r.text}")

class NexusRawUpload():
    def __init__(self, path: str, version: str, user: str, password: str, merge: str = "manual") -> None:
        if path.endswith("/"): path = path[:-1]
        self.auth = (user, password)
        self.path = path
        self.project_name = path.split("/")[-1]
        self.version = version
        self.merge = self._prepare_merge(merge)
        self.check_server()
        self._check_repository()

    # Prepares merge variable
    @staticmethod
    def _prepare_merge(merge: str) -> int:
        if merge == "manual":
            x = input("Replace package?[y/N]")
            if x == "y":
                return 1
            return 0
        elif merge == "replace":
            return 1
        elif merge == "overwrite":
            return 2
        elif merge == "append":
            return 3
        raise ModuleNotFoundError("Wrong merge method")
    
    # Checks if server is up
    def check_server(self) -> None:
        try:
            r = requests.get(CONFIG_DATA['SERVER_URI'], auth=self.auth)
            if not r.ok:
                raise ConnectionRefusedError(f"Server {CONFIG_DATA['SERVER_URI']} check failed")
        except:
            raise ConnectionRefusedError(f"Server {CONFIG_DATA['SERVER_URI']} check failed")
    
    # Checks if repository with provided name exists
    def _check_repository(self) -> None:
        reps = requests.get(f"{CONFIG_DATA['SERVER_URI']}/service/rest/v1/repositories", auth=self.auth).json()
        for rep in reps:
            if rep["name"] == self.project_name:
                return
        raise IndexError(f"Repository {self.project_name} not found")
    
    # Get repository components to be removed
    def _get_delete_rep(self) -> list:
        r = requests.get(f"{CONFIG_DATA['SERVER_URI']}/service/rest/v1/components?repository={self.project_name}", auth=self.auth)
        if r.ok:
            result = []
            for item in r.json()["items"]:
                if item["name"].startswith(f"{self.project_name}-{self.version}"):
                    result.append((item["id"], item["name"]))
            return result
        return []
    
    # Get all components
    # [(os_filepath1, nexus_path1), ...]
    def _get_all_components(self) -> list:
        result = []
        for path, _, files in os.walk(self.path):
            for name in files:
                if name == ".DS_Store": continue # Exclude macOS .ds_store files
                filepath = "/".join((path.replace("\\", "/"), name))
                result.append((filepath, filepath.replace(self.path, "")[1:]))
        return result
    
    # Handle component: uploads if not symlink, else adds component index to list
    def _handle_component(self, component: tuple, symlinks: list, comp_index: int) -> None:
        if not os.path.islink(component[0]):
            comp_id = self._get_component_id(component[1])
            if self._handle_merge(comp_id):
                self._send_upload_request(component[0], component[1])
        else:
            symlinks.append(comp_index)

    # Handle merge logic & user questions
    def _handle_merge(self, comp_id: str | None) -> bool:
        if self.merge == 0: # Manual
            if comp_id == None:
                return True
            tmp = input("Overwrite?[y/o/a/N]")
            if tmp == "y":
                return True
            elif tmp == "o":
                self.merge = 2
                return True
            elif tmp == "a":
                self.merge = 3
                if comp_id == None:
                    return True
                return False
            elif tmp == "N":
                return False
        elif self.merge == 1: # Replace: upload all files
            return True
        elif self.merge == 2: # Overwrite: upload all files
            return True
        elif self.merge == 3: # Append: upload if comp_id == None
            if comp_id == None:
                return True
            return False

    # Get component from repository
    def _get_component_id(self, endpoint: str) -> str | None:
        comp_path = f"{self.project_name}-{self.version}/{self.project_name}/{endpoint}"
        r = requests.get(f"{CONFIG_DATA['SERVER_URI']}/service/rest/v1/components?repository={self.project_name}", auth=self.auth)
        if r.ok:
            for item in r.json()["items"]:
                if item["name"] == comp_path:
                    return item["id"]
        return None
        
    # Uploads component to provided repository
    def _send_upload_request(self, upload_from: str, endpoint: str):
        log("Uploading component", endpoint)
        with open(upload_from, 'rb') as f:
            data = f.read()
        r = requests.put(f"{CONFIG_DATA['SERVER_URI']}/repository/{self.project_name}/{self.project_name}-{self.version}/{self.project_name}/{endpoint}", data=data, auth=self.auth)
        if not r.ok:
            log(f"Upload failed: Status code {r.status_code}\n{r.text}")

    # Generates file with all symlinks data
    def _generate_metadata_file(self, symlinks: list, components: list) -> bytes:
        text = "symlinks:\n"
        for i in symlinks:
            text += f"   {components[i][1]} {os.readlink(components[i][0])}\n"
        return str.encode(text)
    
    # Sends metadata file
    def _send_metadata_file(self, data: bytes) -> None:
        r = requests.put(f"{CONFIG_DATA['SERVER_URI']}/repository/{self.project_name}/{self.project_name}-{self.version}/.metadata", auth=self.auth, data=data)
        if not r.ok:
            log(f"Metadata upload failed: Status code {r.status_code}\n{r.text}")
    
    # Sends delete component request
    def _delete_comp(self, comp_id: str, comp_path: str) -> None:
        r = requests.delete(f"{CONFIG_DATA['SERVER_URI']}/service/rest/v1/components/{comp_id}", auth=self.auth)
        log(f"Deleted component {comp_path}")

    # Uploads components one by one
    def start(self) -> None:
        if self.merge == 1:
            log(f"Removing old {self.project_name}-{self.version}...")
            remove_comps = self._get_delete_rep()
            for comp in remove_comps:
                self._delete_comp(comp[0], comp[1])
            log(f"Successfully removed old {self.project_name}-{self.version}")
        components = self._get_all_components()
        symlinks = []
        log(f"Uploading {self.project_name}-{self.version}...")
        for _ in range(len(components)):
            self._handle_component(components[_], symlinks, _)
        self._send_metadata_file(self._generate_metadata_file(symlinks, components))
        log(f"Successfully uploaded {self.project_name}-{self.version}")


def check_arguments(args):
    if not args.command:
        print("Error, provide one of following commands: download, upload, config")
        exit(1)
    if not args.auth and CONFIG_DATA["AUTH"] == "" and (args.command != "config" and not args.config_print):
        print("Error, provide auth credentials or update config")
        exit(1)
    if args.command == "upload":
        if not args.version:
            print("Error, provide version tag using --version")
            exit(1)
        if not args.path:
            print("Error, provide path to project using --path")
            exit(1)
    elif args.command == "config":
        if not args.config_auth and not args.config_server:
            print("Error, provide new auth (--config_auth) or new server uri (--config_server)")
            exit(1)

def get_arguments():
    parser = ArgumentParser(description="Script for download & upload binary dependencies")
    parser.add_argument('command', metavar='COMMAND', help="One of the following commands: download, upload, config", type=str, nargs='?', choices=["download", "upload", "config"])
    parser.add_argument("-a", "--auth", help="Nexus user credentials <USER>:<PASSWORD>", type=str, required=False, default="")
    # Upload arguments
    parser.add_argument("-v", "--version", help="Version tag", type=str, required=False)
    parser.add_argument("-p", "--path", help="Path to project that will be uploaded", type=str, required=False)
    parser.add_argument("-m", "--merge", help="Merge argument", type=str, required=False, choices=["manual", "replace", "overwrite", "append"],default="manual")
    # Download arguments
    parser.add_argument("-fp", "--platform", help="Download platform filter", type=str, required=False, default="")
    parser.add_argument("-fa", "--architecture", help="Download architecture filter", type=str, required=False, default="")
    parser.add_argument("-ft", "--target", help="Download target filter", type=str, required=False, default="")
    parser.add_argument("-e", "--external_config", help="Path to external.config", type=str, required=False, default="")
    parser.add_argument("-r", "--recursive", help="Do recursive download", required=False, action="store_true")
    # Configure arguments
    parser.add_argument("-ca", "--config_auth", help="Configure auth credentials", type=str, required=False, default="")
    parser.add_argument("-cs", "--config_server", help="Configure server uri", type=str, required=False, default="http://localhost:8081")
    parser.add_argument("-cp", "--config_print", help="Prints current config settings", required=False, action="store_true")
    return parser.parse_args()

def main() -> None:
    args = get_arguments()
    check_arguments(args)
    if args.command == "download":
        if not args.auth:
            p = NexusRawDownload(
                user=CONFIG_DATA["AUTH"].split(":")[0],
                password=CONFIG_DATA["AUTH"].split(":")[1],
                filter_options=(args.platform, args.architecture, args.target),
                config_path=args.external_config,
                force_download=False
            )
        else:
            p = NexusRawDownload(
                user=args.auth.split(":")[0],
                password=args.auth.split(":")[1],
                filter_options=(args.platform, args.architecture, args.target),
                config_path=args.external_config,
                force_download=False
            )
        if args.recursive:
            p.start_recursive()
        else:
            p.start()
    elif args.command == "upload":
        if not args.auth:
            p = NexusRawUpload(
                user=CONFIG_DATA["AUTH"].split(":")[0],
                password=CONFIG_DATA["AUTH"].split(":")[1],
                path=args.path,
                version=args.version,
                merge=args.merge
            )
        else:
            p = NexusRawUpload(
                user=args.auth.split(":")[0],
                password=args.auth.split(":")[1],
                path=args.path,
                version=args.version,
                merge=args.merge
            )
        p.start()
    elif args.command == "config":
        if args.config_print:
            print_config()
        if args.config_auth:
            update_config("AUTH", args.config_auth)
        if args.config_server:
            update_config("SERVER_URI", args.config_server)

if __name__ == "__main__":
    main()
