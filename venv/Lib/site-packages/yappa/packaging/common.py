import platform

from click import ClickException

REQUIRED_PACKAGES = ("httpx", "PyYAML")
ENCODING = "utf-8"
IS_WINDOWS = any(platform.win32_ver())


def validate_requirements_file(requirements_filename):
    if IS_WINDOWS:
        return
    try:
        with open(requirements_filename, encoding=ENCODING) as f:
            requirements = f.read()
    except FileNotFoundError:
        raise ClickException(
            "Couldn't find requirements file. Please specify "
            "it in yappa.yaml"
        )
    for package in REQUIRED_PACKAGES:
        if package not in requirements:
            raise ClickException(
                f"{package} package should be in requirements."
                "Please update requirements running "
                "'$pip freeze > requirements.txt'"
            )


def env_vars_to_string(env_vars):
    return {k: str(v) for k, v in env_vars.items()}
