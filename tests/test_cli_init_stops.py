from pathlib import Path

import pytest
import yaml

from speech_to_sheets.cli.init import run_init
from speech_to_sheets.sheets.errors import SheetsError
from tests.init_sheet import URL, book, opener
from tests.scripted import Script

CLEAN = (URL, "2", "", "Europe/Madrid", "U0123ABC", "", "en")


@pytest.fixture
def config(tmp_path: Path, env: dict, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", env["GOOGLE_SERVICE_ACCOUNT_FILE"])
    return tmp_path / "config.yaml"


def test_an_existing_config_is_kept_unless_the_user_confirms(config: Path) -> None:
    config.write_text("old: true\n")
    opened: list = []
    script = Script("")  # the default answer is no
    assert run_init(config, Path(".env"), script.prompter, opener(book(), opened)) == 1
    assert config.read_text() == "old: true\n"
    assert opened == []
    assert script.questions == [f"{config} already exists. Replace it? [y/N]: "]


def test_an_existing_config_is_replaced_when_confirmed(config: Path) -> None:
    config.write_text("old: true\n")
    script = Script("y", *CLEAN)
    assert run_init(config, Path(".env"), script.prompter, opener(book(), [])) == 0
    assert yaml.safe_load(config.read_text(encoding="utf-8"))["sheets"]["tab"] == "Expenses"


def test_without_the_google_key_nothing_is_asked(
    config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    script = Script()
    assert run_init(config, config.parent / ".env", script.prompter, opener(book(), [])) == 1
    assert "GOOGLE_SERVICE_ACCOUNT_FILE is not set" in script.output
    assert not config.exists()


def test_a_sheets_error_stops_before_writing(config: Path) -> None:
    def refuse(key_file: Path, sheet_id: str) -> None:
        raise SheetsError("sheets.sheet_id: no spreadsheet with this ID is shared with bot@x")

    script = Script(URL)
    assert run_init(config, Path(".env"), script.prompter, refuse) == 1
    assert script.said == [
        "Failed: sheets.sheet_id: no spreadsheet with this ID is shared with bot@x",
        "Nothing written.",
    ]
    assert not config.exists()
