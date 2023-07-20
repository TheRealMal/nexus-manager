# -*- coding: utf-8 -*-
from datetime import datetime
from hashlib import sha1
import requests
import os

CURRENT_PATH = os.getcwd().replace("\\", "/")

SERVER_URI = "http://localhost:8081"

from private import USER, PASSWORD

def log(*args) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]", end=" ")
    for arg in args:
        print(arg, end=" ")
    print(end="\n")

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
    @staticmethod
    def _check_server() -> None:
        try:
            r = requests.get(SERVER_URI)
            if not r.ok:
                raise ConnectionRefusedError(f"Server {SERVER_URI} check failed")
        except:
            raise ConnectionRefusedError(f"Server {SERVER_URI} check failed")
        
    # Downloads projects one by one
    def start(self) -> None:
        for task in self.tasks:
            self._start_task(task[0], task[1])

    # Download project function
    def _start_task(self, project_name: str, version: str) -> None:
        rep_components = self._get_rep(project_name, self.auth)
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
    def _get_rep(self, rep_name: str, auth: tuple) -> list:
        r = requests.get(f"{SERVER_URI}/service/rest/v1/components?repository={rep_name}", auth=auth)
        if r.ok:
            return [(item["name"], item["assets"][0]["checksum"]["sha1"]) for item in r.json()["items"]]
        return []
    
    # Filter components by platform/architecture/target
    def _filter(self, filter: list) -> bool:
        for _ in range(3):
            if self.filter[_] and self.filter[_] != filter[_]:
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
        r = requests.get(f"{SERVER_URI}/repository/{endpoint}", stream=True, auth=self.auth)
        if r.ok:
            if not_silent: log("Saving file to", download_to_path)
            with open(download_to_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 8):
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        os.fsync(f.fileno())
            return
        if not_silent: log(f"Download failed: Status code {r.status_code}\n{download_to_path}\n{r.text}")

class NexusRawUpload():
    def __init__(self, path: str, version: str, user: str, password: str) -> None:
        if path.endswith("/"): path = path[:-1]
        self.auth = (user, password)
        self.path = path
        self.project_name = path.split("/")[-1]
        self.version = version
        self.check_server()
        self._check_repository()

    # Checks if server is up
    @staticmethod
    def check_server() -> None:
        try:
            r = requests.get(SERVER_URI)
            if not r.ok:
                raise ConnectionRefusedError(f"Server {SERVER_URI} check failed")
        except:
            raise ConnectionRefusedError(f"Server {SERVER_URI} check failed")
    
    # Checks if repository with provided name exists
    def _check_repository(self) -> None:
        reps = requests.get(f"{SERVER_URI}/service/rest/v1/repositories", auth=self.auth).json()
        for rep in reps:
            if rep["name"] == self.project_name:
                return
        raise IndexError(f"Repository {self.project_name} not found")

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
            self._send_upload_request(component[0], component[1])
        else:
            symlinks.append(comp_index)

    # Uploads component to provided repository
    def _send_upload_request(self, upload_from: str, endpoint: str):
        log("Uploading file", endpoint)
        with open(upload_from, 'rb') as f:
            data = f.read()
        r = requests.put(f"{SERVER_URI}/repository/{self.project_name}/{self.project_name}-{self.version}/{self.project_name}/{endpoint}", data=data, auth=self.auth)
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
        r = requests.put(f"{SERVER_URI}/repository/{self.project_name}/{self.project_name}-{self.version}/.metadata", auth=self.auth, data=data)
        if not r.ok:
            log(f"Metadata upload failed: Status code {r.status_code}\n{r.text}")

    # Uploads components one by one
    def start(self) -> None:
        components = self._get_all_components()
        symlinks = []
        for _ in range(len(components)):
            self._handle_component(components[_], symlinks, _)
        self._send_metadata_file(self._generate_metadata_file(symlinks, components))

def main() -> None:
    a = NexusRawDownload(
        user=USER,
        password=PASSWORD,
        filter_options=("macos", None, None),
        config_path="/Users/therealmal/Desktop/Workspace/nexus-manager/tests2",
        force_download=False
    )
    a.start()
    # b = NexusRawUpload(
    #     user=USER,
    #     password=PASSWORD,
    #     path="/Users/therealmal/Desktop/Workspace/nexus-manager/tests/external/raw-test",
    #     version="0.0.2"
    # )
    # b.start()
    pass

if __name__ == "__main__":
    main()
