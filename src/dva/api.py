import os
import re
import json
import hashlib
import pycurl
from pyDataverse.api import NativeApi, DataAccessApi
from pyDataverse.models import Datafile
from dva.config import Config
from io import BytesIO


class APIException(Exception):
    pass


def dataverse_file_download(base_url, persistent_id, api_token, path):
    dvurl = f"{base_url}api/access/datafile/{persistent_id}"
    with open(path, 'wb') as f:
        c = pycurl.Curl()
        c.setopt(c.URL, dvurl)
        c.setopt(pycurl.HTTPHEADER, [f'X-Dataverse-key: {api_token}'])
        c.setopt(c.WRITEDATA, f)
        c.perform()
        status_code = c.getinfo(pycurl.HTTP_CODE)
        if status_code != 200:
            os.unlink(f.name)
        c.close()
        if status_code != 200:
            raise APIException(f"Failed to download file status:{status_code}")


def dataverse_file_upload(base_url, persistent_id, api_token, path, directory_label):
    buffer = BytesIO()
    dvurl = f"{base_url}/api/datasets/:persistentId/add?persistentId={persistent_id}"
    c = pycurl.Curl()
    c.setopt(c.URL, dvurl)
    c.setopt(pycurl.HTTPHEADER, [f'X-Dataverse-key: {api_token}'])
    c.setopt(c.POST, 1)
    c.setopt(c.WRITEDATA, buffer)
    payload = {
        "directoryLabel": directory_label,
        "tabIngest":"false"
    }
    c.setopt(c.HTTPPOST, [
        ("file", (c.FORM_FILE, path)),
        ("jsonData", json.dumps(payload) )
    ])
    c.perform()
    status_code = c.getinfo(pycurl.HTTP_CODE)
    c.close()
    return buffer.getvalue().decode('utf-8'), status_code


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
        directory_label = dvfile.get("directoryLabel", "")
        filename = dvfile["dataFile"]["filename"]
        persistent_id = dvfile["dataFile"]["id"]
        if directory_label:
            path = os.path.join(dest, directory_label, filename)
        else:
            path = os.path.join(dest, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        dataverse_file_download(
            base_url=self._api.base_url,
            persistent_id=persistent_id,
            api_token=self._api.api_token,
            path=path
        )
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
        payload, status_code = dataverse_file_upload(
            base_url=self._api.base_url,
            persistent_id=doi,
            api_token=self._api.api_token,
            path=path,
            directory_label=dirname
        )
        if status_code >= 500:
            raise APIException(f"Received {status_code} error.\n\n{payload}")
        else:
            if status_code != 200:
                data = json.loads(payload)
                raise APIException(data.get("status") + " " + data.get("message"))

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
