from pathlib import Path

import pytest
from pydantic import ValidationError

from speech_to_sheets.config.errors import describe
from speech_to_sheets.config.secrets import Secrets


def test_valid_values_load_and_are_masked(env: dict[str, str]) -> None:
    secrets = Secrets.model_validate(env)
    assert secrets.slack_bot_token.get_secret_value() == "xoxb-test-bot"
    assert "xoxb-test-bot" not in repr(secrets)
    assert "sk-test-anthropic" not in str(secrets)


def test_swapped_slack_tokens_are_rejected(env: dict[str, str]) -> None:
    swapped = {**env, "SLACK_BOT_TOKEN": env["SLACK_APP_TOKEN"], "SLACK_APP_TOKEN": "xoxb-x"}
    with pytest.raises(ValidationError, match="must start with xoxb-"):
        Secrets.model_validate(swapped)


def test_missing_google_key_file_is_rejected(env: dict[str, str], tmp_path: Path) -> None:
    missing = {**env, "GOOGLE_SERVICE_ACCOUNT_FILE": str(tmp_path / "nope.json")}
    with pytest.raises(ValidationError, match="no such file"):
        Secrets.model_validate(missing)


def test_error_text_never_contains_the_secret_value(env: dict[str, str]) -> None:
    bad = {**env, "SLACK_BOT_TOKEN": "not-a-bot-token-SECRET"}
    with pytest.raises(ValidationError) as caught:
        Secrets.model_validate(bad)
    assert "SECRET" not in str(caught.value)
    assert "SECRET" not in " ".join(describe(caught.value))
