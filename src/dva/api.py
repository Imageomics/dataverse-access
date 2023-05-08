import os
import re
import hashlib
import requests
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

    def _download_datafile(self, dvfile, dest):
        dv_data_file = dvfile["dataFile"]
        # Retrieve the original file (that matches MD5 checksum) for files processed by Dataverse ingress
        data_format = None
        if dv_data_file.get("originalFileFormat"):
            data_format = "original"

        # code from pyDataverse
        url = "{0}/datafile/{1}".format(
                self._data_api.base_url_api_data_access, dv_data_file["id"]
        )
        if data_format:
            url += "&format={0}".format(data_format)
        headers = {
            "X-Dataverse-key": self._data_api.api_token
        }
        with requests.get(url, headers=headers, stream=True) as resp:
            resp.raise_for_status()
            filename = self.get_download_filename(resp)
            directory_label = dvfile.get("directoryLabel", "")
            if directory_label:
                path = os.path.join(dest, directory_label, filename)
            else:
                path = os.path.join(dest, filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            resp.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
        return path

    def download_file(self, dvfile, dest):
        return self._download_datafile(dvfile, dest)

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
