# Nexus Manager
Sonatype Nexus Raw repositories manager.  
Downloads projects versions from external.config file & Uploads project version to Sonatype Nexus repository.
## Usage
```console
nexmanager <COMMAND> [FLAGS]
```
### external.config structure
By default **download** script searchs for `external.config` in current directory, but you can specify it by using flag `--external-config`
```
<project_name1> <version1>
# Comment
<project_name2> <version2> # Comment
...
```
## Commands
| Command name | Utility                                            |
|--------------|----------------------------------------------------|
| upload       | Upload project version                             |
| download     | Download versions of projects from external.config |
| config       | Configure auth and server uri                      |
### Flags
```diff
# Upload flags:
-a --auth (Optional if credentials saved to config)
Nexus user credentials. Format: <USER>:<PASSWORD>
-v --version (Required for this command)
Project version tag.
-p --path (Required for this command)
Path to project that will be uploaded
-m --merge (Optional)
Merge parameter
  manual    - Choose what to do while uploading every component
  replace   - Remove provided project version and upload a new one
  overwrite - Overwrite files if they exist
  append    - Upload only new files

# Download flags:
-a --auth (Optional if credentials saved to config)
Nexus user credentials. Format: <USER>:<PASSWORD>
-p --platform (Optional)
Filters downloading components by platform if provided
-t --target (Optional)
Filters downloading components by target if provided
-e --external-config (Optional)
Path to external.config directory, current directory by default
-r --recursive (Optional)
Do recursive download if provided
-f --force (Optional)
Replaces all files

# Config flags: (One of them required for this command)
-a --auth
Configure auth credentials
-s -- server
Configure server uri
-p --print
Prints current config settings
```
## Repositories structure
Repository must be created by user via web interface, because sonatype nexus API does not support repository creation.
```console
${project_name1} <- Repository name (Same as project name)
	${project_name1}-${version_tag} <- Project name w/ version tag
		${project_name1}
			${platform}-${architecture}-${target} <- Build params
				example_directory1
				example_file1
				example_file2
				...
${project_name2}
	...
```
## Build and setup whl file
Go to nexus-manager directory and run this command to build `.whl` file
```console
python3 setup.py bdist_wheel
```
Build `.whl` file or download it from `Releases` section, go to directory with that file and run command in such format to install tool
```console
pip install Nexus_Manager-<version>-<params>.whl
```
## TODO
- [x] Create test nexus Raw repository
- [x] Make NexusRawDownload module
- [x] Make NexusRawUpload module
- [x] Check existing files (filename + sha1)
- [x] Add platform/architecture/target download filter
- [x] Add merge support for future CLI (--merge={manual, replace, overwrite, append})
- [x] Add recursive download function
- [x] Add handler for symbol link files
- [x] Make command line interface
- [x] Add config for server and user credentials
- [x] Build WHL file

