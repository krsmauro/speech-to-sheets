from collections.abc import Callable
from pathlib import Path

import pytest

from speech_to_sheets.config.errors import ConfigError
from speech_to_sheets.config.settings import load_settings
from tests.conftest import valid_yaml

NO_ENV_FILE = Path("does-not-exist.env")


def test_missing_secrets_are_all_reported_by_variable_name(write_config: Callable) -> None:
    path = write_config(valid_yaml())
    with pytest.raises(ConfigError) as caught:
        load_settings(path, NO_ENV_FILE, {})
    message = str(caught.value)
    for name in ("SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "ANTHROPIC_API_KEY"):
        assert name in message
    assert "GOOGLE_SERVICE_ACCOUNT_FILE" in message


def test_empty_secret_counts_as_missing(write_config: Callable, env: dict) -> None:
    path = write_config(valid_yaml())
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        load_settings(path, NO_ENV_FILE, {**env, "ANTHROPIC_API_KEY": ""})


def test_invalid_secret_is_reported_without_its_value(write_config: Callable, env: dict) -> None:
    bad = {**env, "SLACK_BOT_TOKEN": "wrong-prefix-SECRET"}
    path = write_config(valid_yaml())
    with pytest.raises(ConfigError) as caught:
        load_settings(path, NO_ENV_FILE, bad)
    assert "SLACK_BOT_TOKEN" in str(caught.value)
    assert "SECRET" not in str(caught.value)


def test_secrets_in_the_config_file_are_refused(write_config: Callable, env: dict) -> None:
    data = {**valid_yaml(), "secrets": {"SLACK_BOT_TOKEN": "xoxb-leaked"}}
    path = write_config(data)
    with pytest.raises(ConfigError, match="belong in") as caught:
        load_settings(path, NO_ENV_FILE, env)
    assert "xoxb-leaked" not in str(caught.value)


def test_secrets_fall_back_to_env_file_and_real_environment_wins(
    write_config: Callable, env: dict, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("\n".join(f"{k}={v}" for k, v in env.items()) + "\n")
    settings = load_settings(write_config(valid_yaml()), env_file, {"ANTHROPIC_API_KEY": "sk-real"})
    assert settings.secrets.slack_app_token.get_secret_value() == "xapp-test-app"
    assert settings.secrets.anthropic_api_key.get_secret_value() == "sk-real"
