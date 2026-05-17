import logging
import os
import subprocess
import sys
from contextlib import suppress
from pathlib import Path
from shutil import copytree, ignore_patterns, make_archive, rmtree

import boto3
import click

from yappa.handlers.common import DEFAULT_CONFIG_FILENAME
from yappa.packaging.common import validate_requirements_file, \
    env_vars_to_string
from yappa.settings import (
    DEFAULT_IGNORED_FILES,
    DEFAULT_PACKAGE_DIR,
    DEFAULT_REQUIREMENTS_FILE,
    HANDLERS_DIR,
    YANDEX_S3_URL,
)
from yappa.utils import get_yc_entrypoint

"""
limitations:
- 128 MB - resulting zip archive
"""

logger = logging.getLogger(__name__)


def prepare_package(
    requirements_file=DEFAULT_REQUIREMENTS_FILE,
    ignored_files=DEFAULT_IGNORED_FILES,
    tmp_dir=DEFAULT_PACKAGE_DIR,
    to_install_requirements=True,
    config_filename=DEFAULT_CONFIG_FILENAME,
):
    """
    prepares package folder
    - copy project files
    - copy handler.py
    - install packages
    """
    validate_requirements_file(requirements_file)

    logger.info("Copying project files to %s", tmp_dir)
    with suppress(FileExistsError):
        os.mkdir(tmp_dir)
    copytree(
        os.getcwd(),
        tmp_dir,
        ignore=ignore_patterns(*ignored_files, tmp_dir, requirements_file),
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
    if to_install_requirements:
        logger.info("Installing requirements...")
        cmd = (
            f"{sys.executable} -m pip install "
            f"-r {requirements_file} -t {tmp_dir} --upgrade --quiet"
        )
        subprocess.check_call(cmd.split())
    return tmp_dir


def ensure_bucket(bucket_name, aws_access_key_id, aws_secret_access_key):
    s3 = boto3.resource(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        endpoint_url=YANDEX_S3_URL,
    )
    bucket = s3.Bucket(bucket_name)
    try:
        bucket.create()
    except Exception as e:
        if e.__class__.__name__ != "BucketAlreadyOwnedByYou":
            raise
    return bucket


def upload_to_bucket(
    folder, bucket_name, aws_access_key_id, aws_secret_access_key
):
    """
    makes archive, uploads to bucket, deletes tmp archive
    """
    logger.info("Creating zip package")
    archive_path = make_archive(folder, "zip", folder)
    archive_filename = os.path.basename(archive_path)
    try:
        bucket = ensure_bucket(
            bucket_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        bucket.upload_file(archive_filename, archive_filename)
    finally:
        os.remove(archive_filename)
        rmtree(folder)
    return archive_filename


def delete_bucket(bucket_name, aws_access_key_id, aws_secret_access_key):
    """
    deletes bucket from s3
    """
    bucket = ensure_bucket(
        bucket_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    bucket.objects.all().delete()
    bucket.delete()


def create_function_version(yc, config, config_filename):
    click.echo("Preparing package...")
    package_dir = prepare_package(
        config["requirements_file"],
        config["excluded_paths"],
        to_install_requirements=True,
        config_filename=config_filename,
    )
    click.echo(f"Uploading to bucket {config['bucket']}...")
    object_key = upload_to_bucket(
        package_dir,
        config["bucket"],
        **yc.get_s3_key(config["service_account_names"]["creator"]),
    )
    click.echo(
        "Creating new function version for "
        + click.style(config["project_slug"], bold=True)
    )
    yc.create_function_version(
        config["project_slug"],
        runtime=config["runtime"],
        description=config["description"],
        bucket_name=config["bucket"],
        object_name=object_key,
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
    if access_changed := yc.set_function_access(
        function_name=config["project_slug"], is_public=config["is_public"]
    ):
        click.echo(
            f"Changed function access. Now it is "
            f" {'not' if config['is_public'] else 'open to'} public"
        )

    if config["django_settings_module"]:
        yc.create_function_version(
            config["manage_function_name"],
            runtime=config["runtime"],
            description=config["description"],
            bucket_name=config["bucket"],
            object_name=object_key,
            entrypoint=get_yc_entrypoint("manage", config["entrypoint"]),
            memory=config["memory_limit"],
            service_account_id=config["service_account_id"],
            timeout=300,
            named_service_accounts=config["named_service_accounts"],
            environment=env_vars_to_string(config["environment"]),
        )
