# Nexus Manager
Sonatype Nexus Raw repositories manager
## TODO
- [x] Create test nexus repository
- [x] Create test nexus Raw repository
- [ ] Make NexusRawDownload module
- [ ] Make NexusRawUpload module
- [ ] Make CLI
- [ ] Make whl packer

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
