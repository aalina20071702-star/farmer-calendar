import logging
import os
from importlib import import_module
from pathlib import Path

import httpx

from .common import (
    DEFAULT_CONFIG_FILENAME,
    body_to_bytes,
    load_yaml,
    patch_response,
    set_access_token,
)

logger = logging.getLogger(__name__)


def load_app(import_path, django_settings_module=None):
    if not import_path:
        raise ValueError("import_path should not be empty")
    os.environ["DJANGO_SETTINGS_MODULE"] = django_settings_module or ""
    *submodules, app_name = import_path.split(".")
    module = import_module(".".join(submodules))
    return getattr(module, app_name)


def call_app(application, event):
    """
    call wsgi application
    see https://cloud.yandex.ru/docs/functions/concepts/function-invoke
    #response
    """
    host_url = event["headers"].get("Host", "https://raw-function.net")
    if not host_url.startswith("http"):
        host_url = f"https://{host_url}"
    body_to_bytes(event)

    with httpx.Client(app=application, base_url=host_url) as client:
        request = client.build_request(
            method=event["httpMethod"],
            url=event["url"],
            headers=event["headers"],
            params=event["queryStringParameters"],
            content=event["body"],
        )
        return client.send(request)


try:
    set_access_token()
    config = load_yaml(
        Path(Path(__file__).resolve().parent.parent, DEFAULT_CONFIG_FILENAME)
    )

    app = load_app(
        config.get("entrypoint"), config.get("django_settings_module")
    )
except ValueError:
    logger.warning("Couldn't load app. Looks like broken Yappa config is used")


def handle(event, context):
    set_access_token()
    if not event:
        return {
            "statusCode": 500,
            "body": "got empty event",
        }
    try:
        response = call_app(app, event)
        return patch_response(response)
    except Exception as e:
        logger.error("unhandled error", exc_info=True)
        return {
            "statusCode": 500,
            "body": f"got unhandled exception ({e}). Most likely on "
            f"Yappa side. See clouds logs for traceback",
        }
