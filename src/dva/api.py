import os
import hashlib
from pyDataverse.api import NativeApi, DataAccessApi
from pyDataverse.models import Datafile
from dva.config import Config


class APIException(Exception):
    pass


class API(object):
    def __init__(self, base_url, api_token):
        self._api = NativeApi(base_url, api_token)
        self._data_api = DataAccessApi(base_url, api_token)

    def get_files_for_doi(self, doi):
        dataset = self._api.get_dataset(doi).json()
        return dataset['data']['latestVersion']['files']

    def download_file(self, dvfile, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        file_id = dvfile["dataFile"]["id"]
        with open(path, "wb") as f:
            # NOTE: the call below blocks until the entire file is retrieved (in memory)
            response = self._data_api.get_datafile(file_id)
            f.write(response.content)

    @staticmethod
    def verify_checksum(dvfile, path):
        checksum = dvfile["dataFile"]["checksum"]
        checksum_type = checksum["type"]
        checksum_value = checksum["value"]
        if checksum_type != "MD5":
            raise APIException(f"Unsupported checksum type {checksum_type}")

        with open(path, 'rb') as infile:
            hash = hashlib.md5(infile.read()).hexdigest()
            if checksum_value != hash:
                raise APIException(f"Hash value mismatch for {path}: {checksum_value} vs {hash} ")

    def upload_file(self, doi, path, dirname=""):
        df = Datafile()
        data = {"pid": doi, "filename": os.path.basename(path)}
        if dirname:
           data["directoryLabel"] = dirname
        df.set(data)
        resp = self._api.upload_datafile(doi, path, df.json())
        status = resp.json()["status"]
        if status != "OK":
           raise APIException(f"Uploading failed with status {status}.")

    @staticmethod
    def get_dvfile_path(dvfile, parent_dir=None):
        path = dvfile["dataFile"]["filename"]
        directory_label = dvfile.get("directoryLabel", "")
        if directory_label:
            path = f"{directory_label}/{path}"
        if parent_dir:
            path = f"{parent_dir}/{path}"
        return path

    @staticmethod
    def get_dvfile_size(dvfile):
        return dvfile["dataFile"]["filesize"]



def get_api(url):
    config = Config(url)
    return API(
        base_url=config.url,
        api_token=config.token
    )
