import os
from collections.abc import Mapping
from pathlib import Path

from dotenv import dotenv_values

from speech_to_sheets.config.errors import ConfigError

GOOGLE_KEY_VARIABLE = "GOOGLE_SERVICE_ACCOUNT_FILE"


def read_env(env_file: Path, environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """Variables from env_file, overridden by the real environment. Empty values count as unset."""
    merged = {**dotenv_values(env_file), **(os.environ if environ is None else environ)}
    return {name: value for name, value in merged.items() if value}


def google_key_file(env_file: Path, environ: Mapping[str, str] | None = None) -> Path:
    """Only the Google key path, for tools that need no Slack or Anthropic secrets."""
    value = read_env(env_file, environ).get(GOOGLE_KEY_VARIABLE)
    if not value:
        raise ConfigError(
            f"{GOOGLE_KEY_VARIABLE} is not set in the environment or {env_file}."
            " See the README, Google Sheets setup."
        )
    path = Path(value).expanduser()
    if not path.is_file():
        raise ConfigError(f"{GOOGLE_KEY_VARIABLE}: no such file: {path}")
    return path
