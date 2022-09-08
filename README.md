# dataverse-container
Docker container to stage [Dataverse](https://dataverse.org/) files.

Environment variables:
- DV_BASE_URL - Required URL for your dataverse
- DV_API_TOKEN - Optional token for accessing unpublished data

## Setup
Create and activate a virtual environment, then install the requirements like so:
```
pip install -r requirements.txt
```

### Upload
Upload files to an existing dataset identified by a doi.
```
python dv.py upload <file_or_folder> <doi>
```

### Download
Download files from a dataset identified by a doi.
```
python dv.py download <doi> <destination_path>
```

### Docker

#### Build and run the Docker container
```
docker build -t dataverse-cli .
docker run -e DV_API_TOKEN=<yourtoken> -e DV_BASE_URL=<yourdvurl> -it dataverse-cli python /src/dv.py ...
```
