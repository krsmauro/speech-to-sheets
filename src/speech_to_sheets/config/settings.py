import os
from collections.abc import Mapping
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from speech_to_sheets.config.errors import ConfigError, describe
from speech_to_sheets.config.secrets import Secrets
from speech_to_sheets.config.sections import (
    DedupeConfig,
    ExtractConfig,
    SheetsConfig,
    SlackConfig,
    SttConfig,
)


class Settings(BaseModel):
    # validate_default makes a missing section report its missing keys, not just the section.
    model_config = ConfigDict(extra="forbid", validate_default=True)

    timezone: str = "UTC"
    slack: SlackConfig = Field(default_factory=dict)
    sheets: SheetsConfig = Field(default_factory=dict)
    stt: SttConfig = Field(default_factory=dict)
    extract: ExtractConfig = Field(default_factory=dict)
    dedupe: DedupeConfig = Field(default_factory=dict)
    secrets: Secrets

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (KeyError, ValueError, OSError):
            raise ValueError("unknown timezone, use an IANA name like Europe/Madrid") from None
        return value


def load_settings(
    config_path: Path = Path("config.yaml"),
    env_file: Path = Path(".env"),
    environ: Mapping[str, str] | None = None,
) -> Settings:
    """Load config.yaml plus secrets from the environment, falling back to env_file.

    Real environment variables win over the .env file. Raises ConfigError listing every problem.
    """
    env = {**dotenv_values(env_file), **(os.environ if environ is None else environ)}
    data = _read_yaml(config_path)
    if "secrets" in data:
        raise ConfigError(f"{config_path}: secrets belong in {env_file}, not in the config file")
    names = [field.alias for field in Secrets.model_fields.values()]
    data["secrets"] = {name: env[name] for name in names if env.get(name)}
    try:
        return Settings.model_validate(data)
    except ValidationError as error:
        lines = "\n".join(f"  - {line}" for line in describe(error))
        raise ConfigError(f"Invalid configuration ({config_path}, {env_file}):\n{lines}") from None


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        raise ConfigError(f"{path} not found. Copy config.example.yaml to {path} and edit it.")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ConfigError(f"{path} is not valid YAML: {error}") from None
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must be a mapping of settings at the top level")
    return data
