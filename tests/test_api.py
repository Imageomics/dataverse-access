import unittest
import hashlib
from unittest.mock import Mock, patch, mock_open, ANY
from dva.api import API, get_api, APIException, dataverse_file_download, dataverse_file_upload

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.url = 'someurl'
        self.token = 'secret'
        self.config = Mock(url=self.url, token=self.token)

    @patch('dva.api.Config')
    @patch('dva.api.NativeApi')
    @patch('dva.api.DataAccessApi')
    def test_get_api(self, mock_data_api, mock_native_api, mock_config):
        mock_config.return_value = self.config
        api = get_api(url=None)
        mock_data_api.assert_called_with(self.url, self.token)
        mock_native_api.assert_called_with(self.url, self.token)

    @patch('dva.api.Config')
    @patch('dva.api.NativeApi')
    @patch('dva.api.DataAccessApi')
    def test_get_files_for_doi(self, mock_data_api, mock_native_api, mock_config):
        response = Mock()
        response.json.return_value = {
            "data": {
                "latestVersion": {
                    "files": [{
                        "dataFile": {
                           "id": 2222
                        }
                    }]
                }
            }
        }
        mock_native_api.return_value.get_dataset.return_value = response
        api = get_api(url=None)
        result = api.get_files_for_doi(doi='doi:10.70122/FK2/WUU4DM')
        print(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["dataFile"]["id"], 2222)

    def test_get_remote_path(self):
        dvfile = {
            "dataFile": {
                "filename": "data.txt"
            }
        }
        result = API.get_remote_path(dvfile)
        self.assertEqual(result, "data.txt")
        dvfile["directoryLabel"] = "results"
        result = API.get_remote_path(dvfile)
        self.assertEqual(result, "results/data.txt")

    @patch('dva.api.dataverse_file_download')
    @patch('dva.api.Config')
    @patch('dva.api.NativeApi')
    @patch('dva.api.DataAccessApi')
    def test_download_file(self, mock_data_api, mock_native_api, mock_config,
                           mock_dataverse_file_download):
        mock_native_api.return_value.base_url = "someurl"
        mock_native_api.return_value.api_token = "secret"
        dvfile = {
            "dataFile": {
                "id": 2222,
                "filename": "data.txt"
            }
        }
        api = get_api(url=None)
        api.download_file(dvfile, dest="/tmp")
        mock_dataverse_file_download.assert_called_with(
            base_url='someurl', persistent_id=2222, api_token='secret', path='/tmp/data.txt'
        )

    @patch('dva.api.Config')
    @patch('dva.api.NativeApi')
    @patch('dva.api.DataAccessApi')
    def test_verify_checksum_good(self, mock_data_api, mock_native_api, mock_config):
        file_data = b"123"
        file_data_hash = hashlib.md5(file_data).hexdigest()
        dvfile = {
            "dataFile": {
                "id": 2222,
                "checksum": {
                    "type": "MD5",
                    "value": file_data_hash
                }
            }
        }
        api = get_api(url=None)
        with patch("builtins.open", mock_open(read_data=b"123")) as mock_file:
            api.verify_checksum(dvfile, "/tmp/data.txt")

    @patch('dva.api.dataverse_file_upload')
    @patch('dva.api.Config')
    @patch('dva.api.NativeApi')
    @patch('dva.api.DataAccessApi')
    @patch('dva.api.Datafile')
    def test_upload(self, mock_datafile, mock_data_api, mock_native_api, mock_config,
                    mock_dataverse_file_upload):
        api = get_api(url=None)
        mock_dataverse_file_upload.return_value = ('{}', 200)
        api.upload_file(doi='doi:10.70122/FK2/WUU4DM', path="/tmp/data.txt")

        mock_dataverse_file_upload.return_value = (
            '{"status":"ERROR", "message":"some failure"}', 400
        )
        with self.assertRaises(APIException) as raised_exception:
            api.upload_file(doi='doi:10.70122/FK2/WUU4DM', path="/tmp/data.txt")
        self.assertEqual(str(raised_exception.exception), "ERROR some failure")

        mock_dataverse_file_upload.return_value = (
            'System Broken', 503
        )
        with self.assertRaises(APIException) as raised_exception:
            api.upload_file(doi='doi:10.70122/FK2/WUU4DM', path="/tmp/data.txt")
        self.assertEqual(str(raised_exception.exception), "Received 503 error.\n\nSystem Broken")

    def test_get_download_filename(self):
        good_values = [
            ('attachment; filename=bob.txt', 'bob.txt'),
            ('attachment; filename="tom.txt"', 'tom.txt'),
            ('attachment; filename="file1.txt"; other="a"', 'file1.txt'),
        ]
        response = Mock()
        for content_disposition, expected_result in good_values:
            response.headers = {'Content-disposition': content_disposition}
            self.assertEqual(expected_result, API.get_download_filename(response))


class TestDataverseFuncs(unittest.TestCase):
    @patch('dva.api.pycurl')
    @patch('dva.api.os')
    def test_dataverse_file_download(self, mock_os, mock_pycurl):
        mock_pycurl.Curl.return_value.getinfo.return_value = 200
        with patch("builtins.open", mock_open()) as mock_file:
            dataverse_file_download(
                base_url="someurl",
                persistent_id="someid",
                api_token="secret",
                path="/tmp/file.txt")
        mock_os.unlink.assert_not_called()
            
        mock_pycurl.Curl.return_value.getinfo.return_value = 400
        with self.assertRaises(APIException) as raised_exception:
            with patch("builtins.open", mock_open()) as mock_file:
                dataverse_file_download(
                    base_url="someurl",
                    persistent_id="someid",
                    api_token="secret",
                    path="/tmp/file.txt")
        self.assertEqual(str(raised_exception.exception), "Failed to download file status:400")
        mock_os.unlink.assert_called_with(ANY)

    @patch('dva.api.pycurl')
    def test_dataverse_file_upload(self, mock_pycurl):
        mock_pycurl.Curl.return_value.getinfo.return_value = 201
        _, status_code = dataverse_file_upload(
            base_url="someurl",
            persistent_id="someid",
            api_token="secret",
            path="/tmp/data.txt",
            directory_label="mydir")
        self.assertEqual(status_code, 201)
