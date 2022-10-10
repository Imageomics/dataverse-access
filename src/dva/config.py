import os
import json


CONFIG_FILE = "~/.dataverse"
CONFIG_FILE_PATH_VAR_NAME = "DATAVERSE_CONFIG_PATH"
CONFIG_URL = "url"
CONFIG_TOKEN = "token"

URL_ENV_VAR_NAME = "DATAVERSE_URL"
TOKEN_ENV_VAR_NAME = "DATAVERSE_API_TOKEN"

MISSING_URL_CONFIG_MESSAGE = """
ERROR: Missing Dataverse URL configuration.

You need to provide a Dataverse URL for this tool.
This can be done with the "DATAVERSE_URL" environment variable or via a config file.

To create the config file run the following command:

dva setup

"""


class MissingURLConfigError(Exception):
    pass


class Config(object):
    def __init__(self, url):
        config_data = _read_config_file()
        self.url = os.environ.get(URL_ENV_VAR_NAME, config_data.get(CONFIG_URL))
        self.token = os.environ.get(TOKEN_ENV_VAR_NAME, config_data.get(CONFIG_TOKEN))
        if url:
            self.url = url
        if not self.url:
            raise MissingURLConfigError(MISSING_URL_CONFIG_MESSAGE)
        # token is optional (it is only needed for unpublished data)


def _read_config_file():
    path = os.environ.get(CONFIG_FILE_PATH_VAR_NAME)
    if not path:
        path = os.path.expanduser(CONFIG_FILE)
    if os.path.exists(path):
        with open(path, 'r') as infile:
            data = json.load(infile)
        return data
    return {}


def save_config_file(url, token):
    payload = {
        CONFIG_URL: url,
        CONFIG_TOKEN: token,
    }
    path = os.path.expanduser(CONFIG_FILE)
    with open(path, 'w') as outfile:
        json.dump(payload, outfile)
    os.chmod(path, 0o600)
