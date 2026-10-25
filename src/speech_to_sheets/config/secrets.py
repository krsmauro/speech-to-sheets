from collections.abc import Callable
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, SecretStr


def _starts_with(prefix: str) -> Callable[[SecretStr], SecretStr]:
    def check(value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith(prefix):
            raise ValueError(f"must start with {prefix}")
        return value

    return check


def _existing_file(value: Path) -> Path:
    path = value.expanduser()
    if not path.is_file():
        raise ValueError(f"no such file: {path}")
    return path


class Secrets(BaseModel):
    """Values read from environment variables or .env. Field aliases are the variable names."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    slack_bot_token: Annotated[SecretStr, AfterValidator(_starts_with("xoxb-"))] = Field(
        alias="SLACK_BOT_TOKEN"
    )
    slack_app_token: Annotated[SecretStr, AfterValidator(_starts_with("xapp-"))] = Field(
        alias="SLACK_APP_TOKEN"
    )
    anthropic_api_key: SecretStr = Field(alias="ANTHROPIC_API_KEY")
    google_key_file: Annotated[Path, AfterValidator(_existing_file)] = Field(
        alias="GOOGLE_SERVICE_ACCOUNT_FILE"
    )
