import click
import os
import json
from dva.api import get_api
from dva.config import save_config_file, MissingURLConfigError

DOI_HELP = "Dataverse 'DOI'"


@click.group()
def cli():
    pass


@click.command()
@click.argument('doi') #, help="Dataverse DOI (Dataset Persistent ID) to list")
@click.option('--url', help="Dataverse URL")
@click.option('-j', '--json', 'json_format', is_flag=True, help="Use JSON output format")
def ls(doi, json_format, url):
    """List files within a Dataverse dataset DOI.

    DOI is the Dataset Persistent ID to list.
    """
    api = get_api(url)
    dvfiles = api.get_files_for_doi(doi)
    if json_format:
        click.echo(json.dumps(dvfiles, indent=4))
    else:
        for dvfile in dvfiles:
            remote_path = api.get_remote_path(dvfile)
            click.echo(remote_path)


@click.command()
@click.argument('doi')
@click.argument('dest')
@click.option('--url', help="Dataverse URL")
def download(doi, dest, url):
    """Download files within dataset DOI to DEST folder.

    DOI is the Dataset Persistent ID to download files from.
    DEST is a local folder to download files into. Use '.' to download into the current directory.
    """
    api = get_api(url)
    for dvfile in api.get_files_for_doi(doi):
        file_id = dvfile["dataFile"]["id"]
        click.echo(f"Downloading file {file_id}")
        path = api.download_file(dvfile, dest)
        click.echo(f"Downloaded file {file_id} to {path}")
        api.verify_checksum(dvfile, path)
        click.echo(f"Verified file checksum for {path}")


@click.command()
@click.argument('src')
@click.argument('doi')
@click.option('--url', help="Dataverse URL")
def upload(src, doi, url):
    """Upload SRC files to a pre-existing dataset(DOI).

    SRC is a local file or folder to upload files from.
    DOI is the Dataset Persistent ID to upload files into.
    """
    api = get_api(url)
    paths_to_upload = []
    if os.path.isfile(src):
       paths_to_upload.append(src)
    else:
       for folder, subfolders, files in os.walk(src):
            for file in files:
                paths_to_upload.append(os.path.join(folder, file))
    for path in paths_to_upload:
        click.echo(f"Uploading {path}")
        api.upload_file(doi, path)


@click.command()
@click.option('--url', prompt="Enter Dataverse URL")
@click.option("--token", prompt="Enter your Dataverse API Token", hide_input=True)
def setup(url, token):
    """Create config file to store a Dataverse URL and token for use by this tool."""
    save_config_file(url=url, token=token)


cli.add_command(setup)
cli.add_command(ls)
cli.add_command(upload)
cli.add_command(download)


def main():
    try:
        cli()
    except MissingURLConfigError as e:
        click.echo(str(e))

if __name__ == '__main__':
    main()
