import os
import re
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

    def _get_datafile_response(self, dvfile):
        dv_data_file = dvfile["dataFile"]
        # Retrieve the original file (that matches MD5 checksum) for files processed by Dataverse ingress
        data_format = None
        if dv_data_file.get("originalFileFormat"):
            data_format = "original"

        # NOTE: the call below blocks until the entire file is retrieved (in memory)
        return self._data_api.get_datafile(dv_data_file["id"], data_format=data_format)

    def download_file(self, dvfile, dest):
        response = self._get_datafile_response(dvfile)
        filename = self.get_download_filename(response)
        directory_label = dvfile.get("directoryLabel", "")
        if directory_label:
            path = os.path.join(dest, directory_label, filename)
        else:
            path = os.path.join(dest, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(response.content)
        return path

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
    def get_remote_path(dvfile):
        path = dvfile["dataFile"]["filename"]
        directory_label = dvfile.get("directoryLabel", "")
        if directory_label:
            path = f"{directory_label}/{path}"
        return path

    @staticmethod
    def get_download_filename(response):
        content_disposition = response.headers['Content-disposition']
        regex = '^ *filename=(.*?)$'
        for part in content_disposition.split(';'):
            found_items = re.findall(regex, part)
            if found_items:
                return found_items[0].strip('"')
        raise APIException(f"Invalid Content-disposition {content_disposition}")

    @staticmethod
    def get_dvfile_size(dvfile):
        return dvfile["dataFile"]["filesize"]


def get_api(url):
    config = Config(url)
    return API(
        base_url=config.url,
        api_token=config.token
    )
