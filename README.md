# Nexus Manager
Sonatype Nexus Raw repositories manager
## Usage
```console
nexus-manager <COMMAND> [FLAGS]
```
## Commands
| Command name | Utility                                            |
|--------------|----------------------------------------------------|
| upload       | Upload project version                             |
| download     | Download versions of projects from external.config |
| config       | Configure auth and server uri                      |
### Flags
```diff
# General flags:
-a --auth (Optional if credentials saved to config)
Nexus user credentials. Format: <USER>:<PASSWORD>

# Upload flags:
-v --version (Required for this command)
Project version tag.
-p --path (Required for this command)
Path to project that will be uploaded
-m --merge (Optional)
Merge parameter
  manual - Choose what to do while uploading every component
  replace - Remove provided project version and upload a new one
  overwrite - Overwrite files if they exist
  append - Upload only new files

# Download flags:
-fp --platform (Optional)
Filters downloading components by platform if provided
-fa --architecture (Optional)
Filters downloading components by architecture if provided
-ft --target (Optional)
Filters downloading components by target if provided
-e --external_config (Optional)
Path to external.config directory, current directory by default
-r --recursive (Optional)
Do recursive download if provided
-fd --force_download (Optional)
Replaces all files

# Config flags: (One of them required for this command)
-ca --config_auth
Configure auth credentials
-cs -- config_server
Configure server uri
-cp --config_print
Prints current config settings
```
## Repositories structure
```console
${projectName1}
	${projectName1}-${versionTag}
		${projectName1}
			${platform}-${architecture}-${target}
				directory1
				file1
				file2
				...
${projectName2}
	...
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
- [x] Make CLI
- [x] Add config for server and user credentials
- [ ] Make WHL packer

