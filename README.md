# dva - Dataverse access
`dva` is a command line tool to upload and download files from a [Dataverse](https://dataverse.org/) instance.

## Requirements
- [python](https://www.python.org/) - version 3.7+

## Installation
Create and activate a virtual environment, then install this tool:
```
python -m pip install git+https://github.com/Imageomics/dataverse-access.git
```

## Configuration
Downloading published data from a Dataverse requires a Dataverse URL.
Uploading or downloading unpublished data requires a Dataverse URL and an [API token](https://guides.dataverse.org/en/latest/user/account.html#api-token).

The Dataverse URL can be specified:
- Using the `--url <url>` argument
- Setting the `DATAVERSE_URL` environment variable
- Within a config file

The Dataverse API token can be specified:
- Setting the `DATAVERSE_API_TOKEN` environment variable
- Within a config file

### Config File Setup
To create the config file run the following command:
```
dva setup
``` 
This command will prompt you for your Dataverse URL and API token and create a config file
with these two values in your home directory. The config file is named `.dataverse` and is in 
JSON format containing keys "url" and "token".

To use an alternate location for the config file set the `DATAVERSE_CONFIG_PATH` environment variable.

## Commands

### List
List files in an existing dataset identified by a doi.
```
dva ls <doi>
```

#### Example
Listing files within published dataset with DOI doi:10.5072/FK2/B7LCCX in https://datacommons.tdai.osu.edu/.
```
dva ls doi:10.5072/FK2/B7LCCX --url https://datacommons.tdai.osu.edu/
```

### Upload
Upload files to an existing dataset identified by a doi.
```
dva upload <file_or_folder> <doi>
```

### Download
Download files from a dataset identified by a doi.
```
dva download <doi> <destination_path>
```

#### Example
Download files from the published dataset with DOI doi:10.5072/FK2/B7LCCX in https://datacommons.tdai.osu.edu/ into a subdirectory named `data`.
```
dva download doi:10.5072/FK2/B7LCCX data --url https://datacommons.tdai.osu.edu/
```

## Docker and Singularity Support
A Docker image is built for each release of `dataverse-access` that can be used with both [Docker](https://www.docker.com/) and [Singularity/Apptainer](https://apptainer.org/). The images are available at [ghcr.io/imageomics/dataverse-access](https://github.com/Imageomics/dataverse-access/pkgs/container/dataverse-access). The images are tagged with the version of each release.

### Docker Download Example
The following example downloads files into a `data` subdirectory of the current working directory:
```
docker run \
    -v $(pwd)/data:/data \
    -it ghcr.io/imageomics/dataverse-access \
    dva download doi:10.5072/FK2/B7LCCX /data --url https://datacommons.tdai.osu.edu/
```
To persist downloaded files when using Docker typically requires mounting a volume.
The above example uses the [-v docker argument](https://docs.docker.com/storage/volumes/#choose-the--v-or---mount-flag) to mount a `data` subdirectory within the current working directory as `/data` in the container.

### Singularity/Apptainer Download Example
The following example downloads files into a `data` subdirectory of the current working directory:
```
singularity run docker://ghcr.io/imageomics/dataverse-access \
     dva download doi:10.5072/FK2/B7LCCX data --url https://datacommons.tdai.osu.edu/
```
Since singularity typically will mount the current working directory the above command does not mount any extra directories.
For help on mounting directories with the singularity command see the [singularity path binding documentation](https://apptainer.org/docs/user/main/bind_paths_and_mounts.html#user-defined-bind-paths).

## Versioning
Releases of dataverse-access follow [Semantic Versioning](https://semver.org/).  Semantic versioning only applies to the `dva` command line interface and not the underlying python code. 
