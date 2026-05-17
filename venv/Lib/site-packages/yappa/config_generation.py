from pathlib import Path

from yappa.handlers.common import DEFAULT_CONFIG_FILENAME, load_yaml
from yappa.settings import DEFAULT_GW_CONFIG_FILENAME
from yappa.utils import save_yaml


def create_default_gw_config(filename=DEFAULT_GW_CONFIG_FILENAME):
    default_config = load_yaml(
        Path(Path(__file__).resolve().parent, DEFAULT_GW_CONFIG_FILENAME)
    )
    save_yaml(default_config, filename)
    return default_config


def inject_function_id(gw_config, function_id, title="yappa gateway"):
    """
    accepts gw config as dict, finds where to put function_id, returns new dict
    """
    gw_config["info"].update(title=title)
    for path, methods in gw_config["paths"].items():  # pylint: disable=W0612
        for method, description in methods.items():  # pylint: disable=W0612
            yc_integration = description.get("x-yc-apigateway-integration")
            if (
                yc_integration
                and yc_integration["type"] == "cloud_functions"
                and not yc_integration["function_id"]
            ):
                yc_integration.update(function_id=function_id)
    return gw_config


def create_default_config(filename=DEFAULT_CONFIG_FILENAME):
    default_config = load_yaml(
        Path(Path(__file__).resolve().parent, "yappa.yaml")
    )
    save_yaml(default_config, filename)
    return default_config
