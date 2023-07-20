# Nexus Manager
Sonatype Nexus Raw repositories manager
## TODO
- [x] Create test nexus Raw repository
- [x] Make NexusRawDownload module
- [x] Make NexusRawUpload module
- [x] Check existing files (filename + sha1)
- [x] Add platform/architecture/target download filter
- [ ] Add config for server and user credentials
- [ ] Add merge support for future CLI (--merge={manual, replace, overwrite, append})
- [ ] Add recursive download function
- [x] Add handler for symbol link files
- [ ] Make CLI
- [ ] Make WHL packer

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
