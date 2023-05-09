import unittest
import hashlib
import json
from unittest.mock import Mock, patch, mock_open
from dva.api import API, get_api, APIException

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

    @patch('dva.api.Config')
    @patch('dva.api.NativeApi')
    @patch('dva.api.DataAccessApi')
    @patch('dva.api.subprocess')
    def test_download_file(self, mock_subprocess, mock_data_api, mock_native_api, mock_config):
        dvfile = {
            "dataFile": {
                "id": 2222,
                "filename": "data.txt"
            }
        }
        mock_native_api.return_value.base_url = 'https://example.com'
        mock_native_api.return_value.api_token = 'secret'
        mock_data_api.return_value.get_datafile.return_value = Mock(headers={
            'Content-disposition': 'attachment; filename="data.txt"'
        })
        api = get_api(url=None)
        api.download_file(dvfile, dest="/tmp")
        mock_subprocess.run.assert_called_with([
            'curl', '-H', 'X-Dataverse-key:secret',
            'https://example.com/api/access/datafile/2222',
            '--output', '/tmp/data.txt'],
            check=True, stdout=mock_subprocess.PIPE)

    @patch('dva.api.Config')
    @patch('dva.api.NativeApi')
    @patch('dva.api.DataAccessApi')
    def test_verify_checksum(self, mock_data_api, mock_native_api, mock_config):
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

    @patch('dva.api.Config')
    @patch('dva.api.NativeApi')
    @patch('dva.api.DataAccessApi')
    @patch('dva.api.Datafile')
    @patch('dva.api.subprocess')
    def test_upload(self, mock_subprocess, mock_datafile, mock_data_api, mock_native_api, 
                    mock_config):
        api = get_api(url=None)
        mock_subprocess.run.return_value.stdout = json.dumps({
            "status": "OK"
        })
        mock_native_api.return_value.base_url = 'https://example.com'
        mock_native_api.return_value.api_token = 'secret'
        api.upload_file(doi='doi:10.70122/FK2/WUU4DM', path="/tmp/data.txt")
        expected_cmd = [
            'curl', '-H', 'X-Dataverse-key:secret',
            '-F', 'file=@/tmp/data.txt',
            '-F', 'jsonData={"directoryLabel": ""}',
            'https://example.com/api/datasets/:persistentId/add?persistentId=doi:10.70122/FK2/WUU4DM'
        ]
        mock_subprocess.run.assert_called_with(expected_cmd, check=True, stdout=mock_subprocess.PIPE)

        mock_subprocess.run.return_value.stdout = json.dumps({
            "status": "ERROR",
            "message": "Failure"
        })
        with self.assertRaises(APIException) as raised_exception:
            api.upload_file(doi='doi:10.70122/FK2/WUU4DM', path="/tmp/data.txt")
        self.assertEqual(str(raised_exception.exception), "ERROR Failure")

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
