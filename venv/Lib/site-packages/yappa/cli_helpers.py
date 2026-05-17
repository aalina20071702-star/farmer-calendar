import functools
import re
from uuid import uuid4

import click
import yaml
from boltons.strutils import slugify
from click import ClickException
from grpc._channel import _InactiveRpcError  # noqa

from yappa.config_generation import create_default_gw_config, inject_function_id
from yappa.handlers.common import load_yaml
from yappa.packaging import direct, s3
from yappa.settings import HANDLERS
from yappa.utils import save_yaml


class NaturalOrderGroup(click.Group):
    def list_commands(self, ctx):
        return self.commands.keys()


def ensure_function(yc, name, description, is_public):
    click.echo("Ensuring function...")
    function, is_new = yc.create_function(
        name, description, is_public=is_public
    )
    if is_new:
        click.echo(
            "Created serverless function:\n\tname: "
            + click.style(f"{function.name}")
            + "\n\tid: "
            + click.style(f"{function.id}")
            + "\n\tinvoke url : "
            + click.style(f"{function.http_invoke_url}", fg="yellow")
        )
    else:
        click.echo(
            "Using existing function:\n\tname: "
            + click.style(f"{function.name}")
            + "\n\tid: "
            + click.style(f"{function.id}")
            + "\n\tinvoke url : "
            + click.style(f"{function.http_invoke_url}", fg="yellow")
        )
    return function


UPLOAD_FUNCTIONS = {
    "s3": s3.create_function_version,
    "direct": direct.create_function_version,
}


def create_function_version(yc, config, strategy, config_filename):
    creator = UPLOAD_FUNCTIONS[strategy]
    return creator(yc, config, config_filename)


def create_gateway(yc, config, function_id):
    gw_config_filename = config["gw_config"]
    gw_config = load_yaml(
        gw_config_filename, safe=True
    ) or create_default_gw_config(gw_config_filename)

    gw_config = inject_function_id(
        gw_config, f"{function_id}", config["project_slug"]
    )
    save_yaml(gw_config, gw_config_filename)
    click.echo(
        "Saved Yappa Gateway config file at "
        + click.style(gw_config_filename, bold=True)
    )
    click.echo("Ensuring api-gateway...")
    gateway, is_new = yc.create_gateway(
        config["project_slug"], yaml.dump(gw_config)
    )
    if is_new:
        click.echo(
            "Created api-gateway:\n\tname: "
            + click.style(f"{gateway.name}")
            + "\n\tid: "
            + click.style(
                f"{gateway.id}",
            )
            + "\n\tdomain : "
            + click.style(f"https://{gateway.domain}", fg="yellow")
        )
    return is_new


def update_gateway(yc, config):
    gateway = yc.get_gateway(config["project_slug"])
    click.echo(f'Updating api-gateway {click.style(f"{gateway.name}", bold=True)}')
    yc.update_gateway(
        gateway.name, config["description"], load_yaml(config["gw_config"])
    )
    click.echo(
        "Updated api-gateway:\n\tname: "
        + click.style(f"{gateway.name}")
        + "\n\tid: "
        + click.style(
            f"{gateway.id}",
        )
        + "\n\tdomain : "
        + click.style(f"https://{gateway.domain}", fg="yellow")
    )


class ValidationError(ClickException):
    pass


def is_valid_bucket_name(bucket_name):
    """
    Checks if an S3 bucket name is valid according to
    https://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html
    """
    if len(bucket_name) < 3 or len(bucket_name) > 63:
        raise ValidationError(
            "Bucket names must be at least 3 and no more "
            "than 63 characters long."
        )
    if bucket_name.lower() != bucket_name or "_" in bucket_name:
        raise ValidationError(
            "Bucket names must not contain uppercase"
            " characters or underscores"
        )
    for label in bucket_name.split("."):
        if (
            len(label) < 1
            or not (label[0].islower() or label[0].isdigit())
            or not (label[-1].islower() or label[-1].isdigit())
        ):
            raise ValidationError(
                "Each label must start and end with a "
                "lowercase letter or a number"
            )
    if all(s.isdigit() for s in bucket_name.split(".")):
        raise ValidationError(
            "Bucket names must not be formatted as an "
            "IP address (i.e. 192.168.5.4)"
        )


def is_valid_entrypoint(entrypoint):
    """
    try to import entrypoint. if is callable, then ok
    """


def is_valid_django_settings_module(django_settings_module):
    """
    try to setup django app
    """


def is_valid_requirements_file(requirements_file):
    """
    try to open requirements. if it matches to re
    """


def get_bucket_name(config):
    """
    generates bucket name, i.e. Yappa Project -> yappa.bucket-32139
    """
    return config["project_slug"].replace("_", ".") + f"-{str(uuid4())[:8]}"


def is_not_empty(string):
    if not string or not string.strip():
        raise ValidationError("should not be empty")


def is_valid_slug(string):
    """
    is has "_" or spaces - raise ViolationError
    """


def get_slug(config):
    return slugify(config["project_name"]).replace("_", "-")


PROMPTS = (
    ("project_name", "My project", [is_not_empty], "What's your project name?"),
    ("project_slug", get_slug, [is_valid_slug], "What's your project slug?"),
    (
        "requirements_file",
        "requirements.txt",
        [is_not_empty, is_valid_requirements_file],
        "Please specify requirements file",
    ),
)


def get_missing_details(config):
    """
    if value is missing in config prompt user
    """
    is_updated = False
    for key, default, validators, question in PROMPTS:
        if config.get(key) is not None:
            continue
        is_updated = True
        default = default(config) if callable(default) else default
        value = click.prompt(question, default=default)
        for validator in validators:
            validator(value)
        config[key] = value
    if not config.get("application_type"):
        application_types = list(HANDLERS)
        application_types.remove("manage")
        config["application_type"] = click.prompt(
            "Please specify application type",
            default=application_types[0],
            type=click.Choice(application_types),
        )
    if not config.get("entrypoint"):
        config["entrypoint"] = click.prompt(
            "Please specify import path for application", default="wsgi.app"
        )
    if (
        not config.get("django_settings_module")
        and config["application_type"] == "Django"
    ):
        config["django_settings_module"] = click.prompt(
            "Please specify your DJANGO_SETTINGS_MODULE",
            default="project.project.settings",
        )
    if config["django_settings_module"]:
        config["manage_function_name"] = f"{config['project_slug']}-manage"
    if not config.get("bucket_name"):
        config["bucket_name"] = get_bucket_name(config)
    return config, is_updated


def safe(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except _InactiveRpcError as e:
            details = e.details()
            if re.search("UNAUTHENTICATED", details, re.IGNORECASE):
                details = "You have expired or incorrect token"
            click.secho(details, fg="red")
            return
        except OSError as e:
            click.secho(e, fg="red")
            return

    return wrapper
