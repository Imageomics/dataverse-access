import os
import hashlib
import requests
from pyDataverse.api import NativeApi, DataAccessApi, ApiAuthorizationError, OperationFailedError
from pyDataverse.models import Datafile
from dva.config import Config


class APIException(Exception):
    pass


class StreamingDataAccessApi(DataAccessApi):
    # Extends DataAccessApi providing a streaming version of get_datafile
    def get_streaming_datafile(self, file_id, data_format=None):
        url = "{0}/datafile/{1}".format(self.base_url_api_data_access, file_id)
        if data_format:
            url += "?"
        if data_format:
            url += "format={0}".format(data_format)
        return self.get_request(url, stream=True)

    def get_request(self, url, params=None, auth=False, **kwargs):
        # Enhances pyDataVerse get_request to pass kwargs to requests.get
        params = {}
        params["User-Agent"] = "pydataverse"
        if self.api_token:
            params["key"] = str(self.api_token)

        try:
            resp = requests.get(url, params=params, **kwargs)
            if resp.status_code == 401:
                error_msg = resp.json()["message"]
                raise ApiAuthorizationError(
                    "ERROR: GET - Authorization invalid {0}. MSG: {1}.".format(
                        url, error_msg
                    )
                )
            elif resp.status_code >= 300:
                if resp.text:
                    error_msg = resp.text
                    raise OperationFailedError(
                        "ERROR: GET HTTP {0} - {1}. MSG: {2}".format(
                            resp.status_code, url, error_msg
                        )
                    )
            return resp
        except ConnectionError:
            raise ConnectionError(
                "ERROR: GET - Could not establish connection to api {0}.".format(url)
            )


class API(object):
    def __init__(self, base_url, api_token, echo):
        self._api = NativeApi(base_url, api_token)
        self._data_api = StreamingDataAccessApi(base_url, api_token)
        self.echo = echo

    def get_files_for_doi(self, doi):
        dataset = self._api.get_dataset(doi).json()
        return dataset['data']['latestVersion']['files']

    def download_file(self, dvfile, path, chunk_size=8192):
        self.echo(f"Downloading {path}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        file_id = dvfile["dataFile"]["id"]
        with open(path, "wb") as f:
            response = self._data_api.get_streaming_datafile(file_id)
            for chunk in response.iter_content(chunk_size=chunk_size):
                f.write(chunk)

    def verify_checksum(self, dvfile, path):
        checksum = dvfile["dataFile"]["checksum"]
        checksum_type = checksum["type"]
        checksum_value = checksum["value"]
        if checksum_type != "MD5":
            raise APIException(f"Unsupported checksum type {checksum_type}")

        with open(path, 'rb') as infile:
            hash = hashlib.md5(infile.read()).hexdigest()
            if checksum_value != hash:
                raise APIException(f"Hash value mismatch for {path}: {checksum_value} vs {hash} ")

        self.echo(f"Verified file checksum for {path}.")

    def upload_file(self, doi, path, dirname=""):
        self.echo(f"Uploading {path}")
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


def create_api(url, echo):
    config = Config(url)
    return API(
        base_url=config.url,
        api_token=config.token,
        echo=echo
    )
