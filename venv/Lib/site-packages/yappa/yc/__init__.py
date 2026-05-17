import json
import os
from contextlib import suppress

import yandexcloud
from click import ClickException

from yappa.settings import DEFAULT_ACCESS_KEY_FILE
from yappa.yc.access import YcAccessMixin
from yappa.yc.functions import YcFunctionsMixin
from yappa.yc.gateway import YcGatewayMixin


class YC(YcAccessMixin, YcFunctionsMixin, YcGatewayMixin):
    def __init__(self, folder_id=None, token=None, service_account_key=None):
        self.sdk = yandexcloud.SDK(
            token=token, service_account_key=service_account_key
        )
        self.service_account_id = (
            service_account_key.get("service_account_id")
            if service_account_key
            else None
        )
        self.token = token
        self.service_account_key = service_account_key
        self.folder_id = folder_id
        self.function = None
        self.gateway = None

    @classmethod
    def setup(cls, token=None, config={}, skip_folder=False):
        """
        - token can be passed directly or read from YC_OAUTH env variable
        - if couldn't get token, trying to read access key from .yc file
        - folder_id is read from yappa_config.yaml or read from
          YC_FOLDER env variable
        """
        credentials = {
            "token": token or os.environ.get("YC_OAUTH"),
        }
        if not credentials["token"]:
            del credentials["token"]
            with suppress(FileNotFoundError):
                with open(DEFAULT_ACCESS_KEY_FILE, "r+", encoding="utf-8") as f:
                    credentials["service_account_key"] = json.loads(f.read())
        if not (
            credentials.get("token") or credentials.get("service_account_key")
        ):
            raise ClickException(
                "Sorry. Looks like you didn't provide OAuth "
                "token. Also couldn't find service account "
                "key at the .yc file. "
                "Please run $ yappa setup"
            )
        if skip_folder:
            return cls(**credentials)
        if folder_id := config.get("folder_id") or os.environ.get("YC_FOLDER"):
            return cls(folder_id=folder_id, **credentials)
        else:
            raise ClickException(
                "Sorry. Couldn't load folder_id from config "
                "file or YC_FOLDER environment variable"
            )
