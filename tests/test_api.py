import unittest
import hashlib
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

    def test_get_dvfile_path(self):
        dvfile = {
            "dataFile": {
                "filename": "data.txt"
            }
        }
        result = API.get_dvfile_path(dvfile, parent_dir="/tmp")
        self.assertEqual(result, "/tmp/data.txt")
        dvfile["directoryLabel"] = "results"
        result = API.get_dvfile_path(dvfile, parent_dir="/tmp")
        self.assertEqual(result, "/tmp/results/data.txt")

    @patch('dva.api.Config')
    @patch('dva.api.NativeApi')
    @patch('dva.api.DataAccessApi')
    def test_download_file(self, mock_data_api, mock_native_api, mock_config):
        dvfile = {
            "dataFile": {
                "id": 2222
            }
        }
        api = get_api(url=None)
        with patch("builtins.open", mock_open()) as mock_file:
            api.download_file(dvfile, path="/tmp/data.txt")
        mock_file.assert_called_with("/tmp/data.txt", "wb")
        mock_file.return_value.write.assert_called_with(
            mock_data_api.return_value.get_datafile.return_value.content
        )

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
    def test_verify_checksum(self, mock_datafile, mock_data_api, mock_native_api, mock_config):
        api = get_api(url=None)
        response = Mock()
        response.json.return_value = {
            "status": "OK"
        }
        mock_native_api.return_value.upload_datafile.return_value = response
        with patch("builtins.open", mock_open(read_data=b"123")) as mock_file:
            api.upload_file(doi='doi:10.70122/FK2/WUU4DM', path="/tmp/data.txt")

        response.json.return_value["status"] = "bad"
        with self.assertRaises(APIException) as raised_exception:
            with patch("builtins.open", mock_open(read_data=b"123")) as mock_file:
                api.upload_file(doi='doi:10.70122/FK2/WUU4DM', path="/tmp/data.txt")
        self.assertEqual(str(raised_exception.exception), "Uploading failed with status bad.")
