# -*- coding: utf-8 -*-
from datetime import datetime
import requests
import os

CURRENT_PATH = os.getcwd().replace("\\", "/")

SERVER_URI = "http://localhost:8081"

def log(*args) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]", end=" ")
    for arg in args:
        print(arg, end=" ")
    print(end="\n")

class NexusRawDownload():
    def __init__(self, user: str, password: str, config_path: str = CURRENT_PATH) -> None:
        self.auth = (user, password)
        self.config_path = config_path
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
        log(f"Downloading {project_name}-{version}...")
        for comp in rep_components:
            if comp.startswith(f"{project_name}-{version}"):
                self._handle_component(project_name, comp)
        log(f"Successfully downloaded {project_name}-{version}")

            
    # Get repository components
    def _get_rep(self, rep_name: str, auth: tuple) -> list:
        r = requests.get(f"{SERVER_URI}/service/rest/v1/components?repository={rep_name}", auth=auth)
        if r.ok:
            return [item["name"] for item in r.json()["items"]]
        return []
    
    # Handle component: generate downloaded file path -> make dirs -> download
    def _handle_component(self, project_name: str, component: str) -> None:
        filepath = "/".join((self.config_path, "external", component))
        filedir = f"{self.config_path}/external/{'/'.join(component.split('/')[:-1])}"
        if not os.path.exists(filedir):
            os.makedirs(filedir)
        self._send_download_request(filepath, f"{project_name}/{component}")

    # Downloads component from rep to given path
    def _send_download_request(self, download_to_path: str, endpoint: str) -> None:
        r = requests.get(f"{SERVER_URI}/repository/{endpoint}", stream=True, auth=self.auth)
        if r.ok:
            log("Saving file to", download_to_path)
            with open(download_to_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 8):
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        os.fsync(f.fileno())
            return
        log(f"Download failed: Status code {r.status_code}\n{r.text}")

class NexusRawUpload():
    def __init__(self, path: str, version: str, user: str, password: str) -> None:
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
    
    # Uploads component to provided repository
    def _send_upload_request(self, upload_from: str, endpoint: str):
        log("Uploading file", endpoint)
        with open(upload_from, 'rb') as f:
            data = f.read()
        r = requests.put(f"{SERVER_URI}/repository/{self.project_name}/{self.project_name}-{self.version}/{endpoint}", data=data, auth=self.auth)
        if not r.ok:
            log(f"Upload failed: Status code {r.status_code}\n{r.text}")

    # Uploads components one by one
    def start(self) -> None:
        components = self._get_all_components()
        for comp in components:
            self._send_upload_request(comp[0], comp[1])

def main() -> None:
    # a = NexusRawDownload("admin", "", "C:/Users/user/Documents/GitHub/nexus-manager/tests")
    # a.start()
    # b = NexusRawUpload("/Users/therealmal/Downloads/nexus-manager/tests/external/raw-test/raw-test", "0.0.1", "admin", "")
    # b.start()
    pass

if __name__ == "__main__":
    main()
