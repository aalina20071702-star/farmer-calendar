import logging
import os
from contextlib import suppress
from pathlib import Path
from shutil import copytree, ignore_patterns, make_archive, rmtree

import click
from click import ClickException

from yappa.handlers.common import DEFAULT_CONFIG_FILENAME
from yappa.packaging.common import validate_requirements_file, ENCODING, \
    IS_WINDOWS, env_vars_to_string
from yappa.settings import (
    DEFAULT_IGNORED_FILES,
    DEFAULT_PACKAGE_DIR,
    DEFAULT_REQUIREMENTS_FILE,
    HANDLERS_DIR,
    MAX_DIRECT_ARCHIVE_SIZE,
)
from yappa.utils import get_yc_entrypoint

logger = logging.getLogger(__name__)
"""
limitations:
- 4 mb - for resulting zip archive
- 5 min - time to install requirements
"""


def clear_requirements(requirements_file):
    """
    removes Yappa package from requirements
    """
    if IS_WINDOWS:
        return
    buffer = []
    with open(requirements_file, "r", encoding=ENCODING) as f:
        buffer.extend(line for line in f if "yappa" not in line)
    with open(requirements_file, "w+", encoding=ENCODING) as f:
        f.write("".join(buffer))


def prepare_package(
    requirements_file=DEFAULT_REQUIREMENTS_FILE,
    ignored_files=DEFAULT_IGNORED_FILES,
    config_filename=DEFAULT_CONFIG_FILENAME,
    tmp_dir=DEFAULT_PACKAGE_DIR,
):
    """
    prepares package folder
    - copy project files
    - copy handler.py
    - copy requirements file and rename it to 'requirements.txt'
    """
    if requirements_file in ignored_files:
        raise ClickException(
            f"Oops. {requirements_file} file should not be in"
            f" excluded paths (at {config_filename})"
        )
    validate_requirements_file(requirements_file)

    logger.info("Copying project files to %s", tmp_dir)
    with suppress(FileExistsError):
        os.mkdir(tmp_dir)

    copytree(
        os.getcwd(),
        tmp_dir,
        ignore=ignore_patterns(*ignored_files, tmp_dir),
        dirs_exist_ok=True,
    )

    copytree(
        Path(Path(__file__).resolve().parent.parent, HANDLERS_DIR),
        Path(tmp_dir, "handlers"),
        dirs_exist_ok=True,
    )

    os.rename(
        Path(tmp_dir, config_filename), Path(tmp_dir, DEFAULT_CONFIG_FILENAME)
    )

    os.rename(
        Path(tmp_dir, requirements_file), Path(tmp_dir, "requirements.txt")
    )
    clear_requirements(Path(tmp_dir, "requirements.txt"))
    return tmp_dir


SUFFIXES = {
    1e6: "MB",
    1e3: "KB",
    1: " bytes",
}


def to_readable_size(size):
    for s, suffix in SUFFIXES.items():
        if size / s > 1:
            return f"{size / s:.3f}{suffix}"



def create_function_version(yc, config, config_filename):
    click.echo("Preparing package...")
    package_dir = prepare_package(
        config["requirements_file"],
        config["excluded_paths"],
        config_filename,
    )
    archive_path = make_archive(package_dir, "zip", package_dir)
    archive_size = os.path.getsize(archive_path)
    try:
        if archive_size > MAX_DIRECT_ARCHIVE_SIZE:
            raise ClickException(
                f"Sorry. Looks like archive size "
                f"({to_readable_size(archive_size)}) is over the limit"
                f" ({to_readable_size(MAX_DIRECT_ARCHIVE_SIZE)})."
                " Try deploying through s3 ($yappa deploy s3)"
            )

        click.echo(
            "Creating new function version for "
            + click.style(config["project_slug"], bold=True)
            + f" ({to_readable_size(archive_size)})"
        )
        with open(archive_path, "rb") as f:
            content = f.read()
            yc.create_function_version(
                config["project_slug"],
                runtime=config["runtime"],
                description=config["description"],
                content=content,
                entrypoint=get_yc_entrypoint(
                    config["application_type"], config["entrypoint"]
                ),
                memory=config["memory_limit"],
                service_account_id=config["service_account_id"],
                timeout=config["timeout"],
                named_service_accounts=config["named_service_accounts"],
                environment=env_vars_to_string(config["environment"]),
            )
            click.echo("Created function version")
            if config["django_settings_module"]:
                click.echo(
                    "Creating new function version for management commands"
                )
                yc.create_function_version(
                    config["manage_function_name"],
                    runtime=config["runtime"],
                    description=config["description"],
                    content=content,
                    entrypoint=get_yc_entrypoint(
                        "manage", config["entrypoint"]
                    ),
                    memory=config["memory_limit"],
                    service_account_id=config["service_account_id"],
                    timeout=60 * 10,
                    named_service_accounts=config["named_service_accounts"],
                    environment=env_vars_to_string(config["environment"]),
                )
    finally:
        os.remove(archive_path)
        rmtree(package_dir)
    if access_changed := yc.set_function_access(
        function_name=config["project_slug"], is_public=config["is_public"]
    ):
        click.echo(
            f"Changed function access. Now it is "
            f" {'not' if config['is_public'] else 'open to'} public"
        )
