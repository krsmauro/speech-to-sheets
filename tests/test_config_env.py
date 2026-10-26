from pathlib import Path

import pytest

from speech_to_sheets.config.env import google_key_file, read_env
from speech_to_sheets.config.errors import ConfigError


def test_environment_wins_over_the_env_file_and_blanks_count_as_unset(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("A=from-file\nB=from-file\nC=\nD\n")
    assert read_env(env_file, {"B": "from-env", "E": ""}) == {"A": "from-file", "B": "from-env"}


def test_a_blank_environment_variable_hides_the_file_value(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("A=from-file\n")
    assert read_env(env_file, {"A": ""}) == {}


def test_a_missing_env_file_is_fine(tmp_path: Path) -> None:
    assert read_env(tmp_path / "missing.env", {"A": "x"}) == {"A": "x"}


def test_google_key_file_found(tmp_path: Path) -> None:
    key = tmp_path / "key.json"
    key.write_text("{}")
    environ = {"GOOGLE_SERVICE_ACCOUNT_FILE": str(key)}
    assert google_key_file(tmp_path / ".env", environ) == key


def test_google_key_file_expands_the_home_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "key.json").write_text("{}")
    environ = {"GOOGLE_SERVICE_ACCOUNT_FILE": "~/key.json"}
    assert google_key_file(tmp_path / ".env", environ) == tmp_path / "key.json"


def test_google_key_file_not_set_points_to_the_setup_guide(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="GOOGLE_SERVICE_ACCOUNT_FILE is not set.*setup-google"):
        google_key_file(tmp_path / ".env", {})


def test_google_key_file_that_does_not_exist(tmp_path: Path) -> None:
    environ = {"GOOGLE_SERVICE_ACCOUNT_FILE": str(tmp_path / "gone.json")}
    with pytest.raises(ConfigError, match="no such file: .*gone.json"):
        google_key_file(tmp_path / ".env", environ)
