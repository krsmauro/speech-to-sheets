from collections.abc import Callable
from pathlib import Path

import pytest

from speech_to_sheets.config.errors import ConfigError
from speech_to_sheets.config.settings import load_settings
from tests.conftest import valid_yaml

NO_ENV_FILE = Path("does-not-exist.env")


def test_minimal_config_loads_with_english_defaults(write_config: Callable, env: dict) -> None:
    settings = load_settings(write_config(valid_yaml()), NO_ENV_FILE, env)
    assert settings.timezone == "UTC"
    assert settings.sheets.columns.date == "Date"
    assert settings.sheets.fallback_categories == []
    assert settings.stt.language == "auto"
    assert settings.dedupe.retention_days == 30
    assert settings.secrets.anthropic_api_key.get_secret_value() == "sk-test-anthropic"


def test_yaml_values_override_defaults(write_config: Callable, env: dict) -> None:
    data = valid_yaml()
    data["timezone"] = "Europe/Madrid"
    data["sheets"]["columns"] = {"date": "Day"}
    data["extract"] = {"example_rows": 10}
    settings = load_settings(write_config(data), NO_ENV_FILE, env)
    assert settings.timezone == "Europe/Madrid"
    assert settings.sheets.columns.date == "Day"
    assert settings.sheets.columns.amount == "Amount"
    assert settings.extract.example_rows == 10


def test_missing_config_file_says_what_to_do(tmp_path: Path, env: dict) -> None:
    with pytest.raises(ConfigError, match=r"not found.*config\.example\.yaml"):
        load_settings(tmp_path / "config.yaml", NO_ENV_FILE, env)


def test_empty_config_reports_every_required_key(write_config: Callable, env: dict) -> None:
    path = write_config("")
    with pytest.raises(ConfigError) as caught:
        load_settings(path, NO_ENV_FILE, env)
    message = str(caught.value)
    for key in ("slack.allowed_user_ids", "sheets.sheet_id", "sheets.tab", "stt.model_path"):
        assert key in message


def test_unknown_top_level_key_is_rejected(write_config: Callable, env: dict) -> None:
    path = write_config({**valid_yaml(), "timezon": "UTC"})
    with pytest.raises(ConfigError, match="timezon"):
        load_settings(path, NO_ENV_FILE, env)


def test_unknown_timezone_is_rejected(write_config: Callable, env: dict) -> None:
    path = write_config({**valid_yaml(), "timezone": "Mars/Base"})
    with pytest.raises(ConfigError, match="unknown timezone"):
        load_settings(path, NO_ENV_FILE, env)


@pytest.mark.parametrize("content", ["a: [unclosed", "- just\n- a list"])
def test_malformed_yaml_is_a_config_error(write_config: Callable, env: dict, content: str) -> None:
    path = write_config(content)
    with pytest.raises(ConfigError):
        load_settings(path, NO_ENV_FILE, env)
