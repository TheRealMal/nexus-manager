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
    def _check_server(self) -> None:
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
        self.user = user
        self.password = password
        self.path = path
        self.project_name = path.split("/")[-1]
        self.version = version


def main() -> None:
    a = NexusRawDownload("admin", "", "C:/Users/user/Documents/GitHub/nexus-manager/tests")
    a.start()

if __name__ == "__main__":
    main()
