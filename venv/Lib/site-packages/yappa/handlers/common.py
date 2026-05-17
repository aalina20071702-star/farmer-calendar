import logging
import os
import re
from base64 import b64decode, b64encode

import httpx
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

logger = logging.getLogger(__name__)
TOKEN_URL = (
    "http://169.254.169.254/computeMetadata/v1/"
    "instance/service-accounts/default/token"
)


def set_access_token(iam_token=None):
    if not iam_token:
        iam_token = ""
        try:
            resp = httpx.get(TOKEN_URL, headers={"Metadata-Flavor": "Google"})
            if resp.status_code == 200:
                iam_token = resp.json()["access_token"]
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            logger.error("couldn't fetch IAM token: %s", e)
    os.environ["IAM_TOKEN"] = iam_token


def load_yaml(file, safe=False):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return yaml.load(f.read(), Loader)
    except FileNotFoundError:
        if safe:
            return {}
        raise


def body_to_bytes(event):
    if not event["body"]:
        pass
    elif event["isBase64Encoded"]:
        event["body"] = b64decode(event["body"])
    else:
        event["body"] = event["body"].encode()


DEFAULT_CONFIG_FILENAME = "yappa.yaml"

ENCODED_CONTENT_TYPES = (
    re.compile(r"image/.*"),
    re.compile(r"video/.*"),
    re.compile(r"audio/.*"),
    re.compile(r".*zip"),
    re.compile(r".*pdf"),
)


def is_binary(response):
    if not response.headers.get("content-type"):
        return False

    content_type = response.headers["content-type"]
    return any(re_.match(content_type) for re_ in ENCODED_CONTENT_TYPES)


def patch_response(response):
    """
    returns Http response in the format of
    {
     'status code': 200,
     'body': body - string or base64-string in case of binary content,
     'headers': {}
    }
    """
    is_binary_ = is_binary(response)
    if is_binary_:
        body = b64encode(response.content).decode("utf-8")
    else:
        body = response.content.decode()
    return {
        "statusCode": response.status_code,
        "headers": dict(response.headers),
        "body": body,
        "isBase64Encoded": is_binary_,
    }
