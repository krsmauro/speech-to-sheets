from pathlib import Path

import pytest
import yaml

from speech_to_sheets.cli.init import run_init
from speech_to_sheets.config.settings import load_settings
from tests.init_sheet import URL, book, opener
from tests.scripted import Script

# Sheet URL, tab 2, accept the columns, timezone, member ID, default model, language.
CLEAN = (URL, "2", "", "Europe/Madrid", "U0123ABC", "", "en")


@pytest.fixture(autouse=True)
def google_key(env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", env["GOOGLE_SERVICE_ACCOUNT_FILE"])


def run(tmp_path: Path, script: Script, spreadsheet: object = None) -> tuple[int, list]:
    opened: list = []
    open_book = opener(spreadsheet or book(), opened)
    code = run_init(tmp_path / "config.yaml", tmp_path / ".env", script.prompter, open_book)
    assert script.answers == [], "every scripted answer should have been asked for"
    return code, opened


def test_clean_mapping_writes_a_config_the_bot_can_load(tmp_path: Path, env: dict) -> None:
    script = Script(*CLEAN)
    code, opened = run(tmp_path, script)
    assert code == 0
    assert opened == [(Path(env["GOOGLE_SERVICE_ACCOUNT_FILE"]), "sheet-123")]
    assert yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8")) == {
        "timezone": "Europe/Madrid",
        "slack": {"allowed_user_ids": ["U0123ABC"]},
        "sheets": {
            "sheet_id": "sheet-123",
            "tab": "Expenses",
            "columns": {
                "date": "When",
                "amount": "Paid",
                "category": "Kind",
                "description": "Details",
            },
            "fallback_categories": [],
        },
        "stt": {"model_path": "models/ggml-large-v3-turbo-q5_0.bin", "language": "en"},
    }
    settings = load_settings(tmp_path / "config.yaml", tmp_path / ".env", env)
    assert settings.sheets.columns.category == "Kind"
    assert "Categories from the dropdown (2): Food, Transport" in script.output


def test_a_wrong_guess_corrected_by_the_user(tmp_path: Path) -> None:
    # Notes is left of Details and has more varied text, so it is guessed as the description.
    spreadsheet = book(headers=("When", "Paid", "Kind", "Notes", "Details"))
    for row, note in zip(spreadsheet.tabs[1].rows[1:], ["a", "b", "c"]):
        row.insert(3, {"effectiveValue": {"stringValue": note}})
    spreadsheet.tabs[1].rows[1][4]["effectiveValue"]["stringValue"] = "Bus"  # Details: 2 values
    script = Script(URL, "2", "n", "", "", "", "2", *CLEAN[3:])
    assert run(tmp_path, script, spreadsheet)[0] == 0
    config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
    assert config["sheets"]["columns"]["description"] == "Details"
    assert "  description: D Notes" in script.output


def test_unreadable_dropdown_asks_for_the_categories(tmp_path: Path) -> None:
    # No dropdown: the category cannot be guessed, so every column is picked by number.
    script = Script(URL, "2", "", "", "1", "", "Food, Transport, Food", *CLEAN[3:])
    assert run(tmp_path, script, book(dropdown=False))[0] == 0
    config = yaml.safe_load((tmp_path / "config.yaml").read_text(encoding="utf-8"))
    assert config["sheets"]["columns"]["category"] == "Kind"
    assert config["sheets"]["fallback_categories"] == ["Food", "Transport"]


def test_a_blank_member_id_is_written_with_a_reminder(tmp_path: Path) -> None:
    script = Script(*CLEAN[:4], "", *CLEAN[5:])
    assert run(tmp_path, script)[0] == 0
    assert "slack.allowed_user_ids" in script.said[-1]
