import unittest
import os
import json
from unittest.mock import Mock, patch, mock_open
from dva.config import Config, save_config_file, MissingURLConfigError

class TestConfig(unittest.TestCase):

    @patch('dva.config.os')
    def test_config_missing_url(self, mock_os):
        mock_os.path.exists.return_value = False # no config file
        mock_os.environ = {} # no environment variables set
        with self.assertRaises(MissingURLConfigError):
            config = Config(url=None)

    @patch('dva.config.os')
    def test_config_missing_url(self, mock_os):
        mock_os.path.exists.return_value = False # no config file
        mock_os.environ = {} # no environment variables set
        with self.assertRaises(MissingURLConfigError):
            config = Config(url=None)

    @patch('dva.config.os')
    def test_config_from_file(self, mock_os):
        mock_os.path.exists.return_value = True # no config file
        mock_os.environ = {}  # no environment variables set
        config_file_data = json.dumps({
            "url": "myurl",
            "token": "secret",
        })
        with patch("builtins.open", mock_open(read_data=config_file_data)) as mock_file:
            config = Config(url=None)
        self.assertEqual(config.url, "myurl")
        self.assertEqual(config.token, "secret")

    @patch('dva.config.os')
    def test_config_env_variables(self, mock_os):
        mock_os.path.exists.return_value = True  # no config file
        config_file_data = json.dumps({
            "url": "myurl-config-file",
            "token": "secret-config-file",
        })
        mock_os.environ = {
            "DATAVERSE_URL": "myurl"
        }
        with patch("builtins.open", mock_open(read_data=config_file_data)) as mock_file:
            config = Config(url=None)
        self.assertEqual(config.url, "myurl")
        self.assertEqual(config.token, "secret-config-file")

        mock_os.environ = {
            "DATAVERSE_URL": "myurl",
            "DATAVERSE_API_TOKEN": "secret"
        }
        with patch("builtins.open", mock_open(read_data=config_file_data)) as mock_file:
            config = Config(url=None)
        self.assertEqual(config.url, "myurl")
        self.assertEqual(config.token, "secret")

    @patch('dva.config.os')
    def test_config_passed_url(self, mock_os):
        mock_os.path.exists.return_value = True  # no config file
        config_file_data = json.dumps({
            "url": "myurl-config-file",
            "token": "secret-config-file",
        })
        mock_os.environ = {
            "DATAVERSE_URL": "myurl"
        }
        with patch("builtins.open", mock_open(read_data=config_file_data)) as mock_file:
            config = Config(url="betterurl")
        self.assertEqual(config.url, "betterurl")
        self.assertEqual(config.token, "secret-config-file")

    @patch('dva.config.os')
    @patch('dva.config.json')
    def test_save_config_file(self, mock_json, mock_os):
        mock_os.path.expanduser.return_value = '/home/user1/.dataverse'
        with patch("builtins.open", mock_open()) as mock_file:
            save_config_file(url='myurl', token='secret')
        mock_file.assert_called_with('/home/user1/.dataverse', 'w')
        expected_payload = { "url": "myurl", "token": "secret"}
        mock_json.dump.assert_called_with(expected_payload, mock_file.return_value)
