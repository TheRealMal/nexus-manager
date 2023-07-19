# Nexus Manager
Sonatype Nexus Raw repositories manager
## TODO
- [x] Create test nexus repository
- [x] Create test nexus Raw repository
- [x] Make NexusRawDownload module
- [x] Make NexusRawUpload module
- [ ] Add recursive download function
- [ ] Add handler for symbol link files
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
