import os
import hashlib
import click
from pyDataverse.api import NativeApi, DataAccessApi
from pyDataverse.models import Datafile


BASE_URL=os.environ.get("DV_BASE_URL")
API_TOKEN = os.environ.get("DV_API_TOKEN", "")
api = NativeApi(BASE_URL, API_TOKEN)
data_api = DataAccessApi(BASE_URL, API_TOKEN)


@click.group()
def cli():
    pass


def get_files_for_doi(doi):
    dataset = api.get_dataset(doi).json()
    return dataset['data']['latestVersion']['files']


def get_dvfile_path(dvfile, parent_dir=None):
    path = dvfile["label"]
    directory_label = dvfile.get("directoryLabel", "")
    if directory_label:
        path = f"{directory_label}/{path}"
    if parent_dir:
        path = f"{parent_dir}/{path}"
    return path


@click.command()
@click.argument('doi')
@click.option('-l', '--long', is_flag=True)
def ls(doi, long):
    for dvfile in get_files_for_doi(doi):
        path = get_dvfile_path(dvfile)
        if long:
            filesize = dvfile["dataFile"]["filesize"]
            click.echo(f"{filesize} {path}")
        else:
            click.echo(path)


@click.command()
@click.argument('src')
@click.argument('dest')
def cp(src, dest):
    src_is_doi = src.startswith("doi:")
    dest_is_doi = dest.startswith("doi:")
    if src_is_doi and dest_is_doi:
       raise click.BadParameter("Only one of SRC and DEST arguments can be a DOI.")
    if not src_is_doi and not dest_is_doi:
       raise click.BadParameter("One one of SRC or DEST arguments must be a DOI.")
    if src_is_doi:
         download(doi=src, dest=dest)
    elif dest_is_doi:
         upload(src=src, doi=dest)


@click.command()
@click.argument('doi')
@click.argument('dest')
def download(doi, dest):
    for dvfile in get_files_for_doi(doi):
        path = get_dvfile_path(dvfile, dest)
        file_id = dvfile["dataFile"]["id"]
        click.echo(f"Downloading {path}, id {file_id}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            response = data_api.get_datafile(file_id)
            f.write(response.content)
        verify_checksum(dvfile, path)


def verify_checksum(dvfile, filepath):
    checksum = dvfile["dataFile"]["checksum"]
    checksum_type = checksum["type"]
    checksum_value = checksum["value"]
    if checksum_type != "MD5":
        raise ValueError(f"Unsupported checksum type {checksum_type}")

    with open(filepath, 'rb') as infile:
        hash = hashlib.md5(infile.read()).hexdigest()
        if checksum_value == hash:
            click.echo(f"Verified file checksum for {filepath}.")
        else:
            raise ValueError(f"Hash value mismatch for {filepath}: {checksum_value} vs {hash} ")


@click.command()
@click.argument('src')
@click.argument('doi')
def upload(src, doi):
    paths_to_upload = []
    if os.path.isfile(src):
       paths_to_upload.append(src)
    else:
       for folder, subfolders, files in os.walk(src):
            for file in files:
                paths_to_upload.append(os.path.join(folder, file))
    for path in paths_to_upload:
        click.echo(f"Uploading {path}")
        df = Datafile()
        data = {"pid": doi, "filename": os.path.basename(path)}
        dirname = os.path.dirname(path)
        if dirname:
           data["directoryLabel"] = dirname
        df.set(data)
        resp = api.upload_datafile(doi, path, df.json())
        status = resp.json()["status"]
        if status != "OK":
           raise Exception(f"Uploading failed with status {status}.")


cli.add_command(ls)
cli.add_command(upload)
cli.add_command(download)
cli.add_command(cp)


if __name__ == '__main__':
    cli()

