import logging
import os
from contextlib import suppress

import click
from click import ClickException

from yappa.cli_helpers import (
    UPLOAD_FUNCTIONS,
    NaturalOrderGroup,
    create_function_version,
    create_gateway,
    ensure_function,
    get_missing_details,
    safe,
    update_gateway,
)
from yappa.config_generation import create_default_config
from yappa.handlers.common import DEFAULT_CONFIG_FILENAME, load_yaml
from yappa.handlers.manage import FORBIDDEN_COMMANDS
from yappa.packaging.s3 import delete_bucket
from yappa.settings import (
    DEFAULT_ACCESS_KEY_FILE,
    ENV_YC_OAUTH,
    YANDEX_OAUTH_URL,
)
from yappa.utils import save_yaml
from yappa.yc import YC
from yappa.yc.access import save_key
from yappa.yc.function_call import call_manage_function

logger = logging.getLogger(__name__)


@click.group(cls=NaturalOrderGroup)
def cli():
    pass


@cli.command(short_help="setup YC access")
@click.argument(
    "config-file",
    type=click.Path(exists=False),
    default=DEFAULT_CONFIG_FILENAME,
)
@click.option(
    "-t", "--token", default="", help="yandex OAuth token", envvar=ENV_YC_OAUTH
)
@safe
def setup(config_file, token):
    """
    setup of cloud access:

    \b
      - asks for OAuth token
      - asks for cloud to work with
      - asks for folder to work with
      - creates service account (editor) and saves access key to .yc
      - saves folder_id and s3_account_name to yappa.yaml


    *you can skip this step if YC_OAUTH and YC_FOLDER in env vars
    (see README for authentication details)
    """
    click.echo("Welcome to " + click.style("Yappa", fg="yellow") + "!")
    if token == os.environ.get(ENV_YC_OAUTH):
        click.echo("Using YC_OAUTH environment variable")
    if not token:
        click.echo(
            "Please obtain OAuth token at "
            + click.style(YANDEX_OAUTH_URL, fg="yellow")
        )
        token = click.prompt("Please enter OAuth token")
    yc = YC.setup(token=token, skip_folder=True)
    clouds = {c.name: c.id for c in yc.get_clouds()}
    cloud_name = click.prompt(
        "Please select cloud",
        type=click.Choice(clouds),
        default=next(reversed(clouds)),
    )
    folders = {f.name: f.id for f in yc.get_folders(clouds[cloud_name])}
    folder_name = click.prompt(
        "Please select folder",
        type=click.Choice(folders),
        default=next(reversed(folders)),
    )
    yc.folder_id = folders[folder_name]
    account = yc.create_service_account(f"yappa-creator-account-{folder_name}")
    save_key(yc.create_service_account_key(account.id))
    click.echo(
        "Saved service account credentials at "
        + click.style(DEFAULT_ACCESS_KEY_FILE, bold=True)
    )
    config = load_yaml(config_file, safe=True) or create_default_config(
        config_file
    )
    config["folder_id"] = folders[folder_name]
    config["service_account_names"]["creator"] = account.name
    save_yaml(config, config_file)
    click.echo(f"Saved Yappa config file at {click.style(config_file, bold=True)}")


@cli.command(short_help="generate config files, create function & api-gateway")
@click.argument(
    "upload-strategy",
    type=click.Choice(UPLOAD_FUNCTIONS.keys()),
    default="direct",
)
@click.argument(
    "config-file",
    type=click.Path(exists=False),
    default=DEFAULT_CONFIG_FILENAME,
)
@safe
def deploy(upload_strategy, config_file):
    """\b
    - generates yappa.yaml (skipped if file exists)
    - creates function
    - creates function version (with uploaded to s3 package)
    - generates yappa-gw.yaml (skipped if file exists)
    - creates api-gateway
    """
    config = load_yaml(config_file, safe=True) or create_default_config(
        config_file
    )
    config, is_updated = get_missing_details(config)
    if is_updated:
        save_yaml(config, config_file)
        click.echo(f"saved Yappa config file at {click.style(config_file, bold=True)}")
    yc = YC.setup(config=config)
    function = ensure_function(
        yc, config["project_slug"], config["description"], True
    )
    if config["django_settings_module"]:
        ensure_function(
            yc, config["manage_function_name"], config["description"], False
        )
    create_function_version(yc, config, upload_strategy, config_file)
    if config["gw_config"]:
        is_new = create_gateway(yc, config, function.id)
        if not is_new:
            update_gateway(yc, config)


@cli.command()
@click.argument(
    "config-file",
    type=click.Path(exists=True),
    default=DEFAULT_CONFIG_FILENAME,
)
@safe
def undeploy(config_file):
    """
    deletes function, api-gateway and bucket
    """
    config = load_yaml(config_file)
    yc = YC.setup(config=config)
    with suppress(ValueError):
        click.echo(f"Deleting function {config['project_slug']}...")
        yc.delete_function(config["project_slug"])
    with suppress(ValueError):
        click.echo(f"Deleting api-gateway {config['project_slug']}...")
        yc.delete_gateway(config["project_slug"])
    with suppress(ValueError):
        click.echo(f"Destroying bucket {config['bucket']}...")
        delete_bucket(
            config["bucket"],
            **yc.get_s3_key(config["service_account_names"]["creator"]),
        )
    click.echo(
        "That's it! Only service account is left.\n"
        + click.style("Bye!", fg="yellow")
    )


@cli.command(
    context_settings=dict(
        ignore_unknown_options=True,
        help_option_names=[],
    )
)
@click.option(
    "--config-file",
    type=click.Path(exists=True),
    default=DEFAULT_CONFIG_FILENAME,
)
@click.argument("command", type=str)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@safe
def manage(config_file, command, args):
    if command in FORBIDDEN_COMMANDS:
        raise ClickException(
            "Sorry. You cannot run this command with Serverless setup"
        )
    config = load_yaml(config_file, safe=False)
    yc = YC.setup(config=config)
    function = yc.get_function(config["manage_function_name"])
    response = call_manage_function(yc, function.id, command, args)
    click.echo(response)


if __name__ == "__main__":
    cli()
