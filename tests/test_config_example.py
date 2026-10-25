from pathlib import Path

import yaml

from speech_to_sheets.config.settings import Settings

EXAMPLE = Path(__file__).resolve().parent.parent / "config.example.yaml"


def test_example_uses_only_keys_the_settings_know() -> None:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["slack"]["allowed_user_id"] = "U0123ABC"
    data["sheets"].update(sheet_id="sheet-123", tab="Expenses")
    data["stt"]["model_path"] = "/models/ggml-test.bin"
    data["secrets"] = {
        "SLACK_BOT_TOKEN": "xoxb-a",
        "SLACK_APP_TOKEN": "xapp-a",
        "ANTHROPIC_API_KEY": "sk-a",
        "GOOGLE_SERVICE_ACCOUNT_FILE": str(EXAMPLE),
    }
    Settings.model_validate(data)


def test_example_has_no_personal_values() -> None:
    text = EXAMPLE.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert text.isascii(), "accented words suggest a personal category or phrase"
    assert data["sheets"]["fallback_categories"] == []
    assert data["slack"]["allowed_user_id"] == ""
    assert "/Users/" not in text and "VoiceInk" not in text
