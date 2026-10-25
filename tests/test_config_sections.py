from pathlib import Path

import pytest
from pydantic import ValidationError

from speech_to_sheets.config.sections import (
    DedupeConfig,
    ExtractConfig,
    SheetsConfig,
    SlackConfig,
    SttConfig,
)


def test_defaults() -> None:
    assert ExtractConfig().model == "claude-haiku-5-5"
    assert ExtractConfig().example_rows == 30
    assert DedupeConfig().retention_days == 30
    assert DedupeConfig().path == Path("dedupe.sqlite")
    stt = SttConfig(model_path="/m.bin")
    assert (stt.whisper_cli, stt.ffmpeg, stt.language) == ("whisper-cli", "ffmpeg", "auto")
    assert stt.timeout_seconds == 120


@pytest.mark.parametrize("user_id", ["", "u0123", "ABC", "U 12", "B0123ABC"])
def test_bad_slack_user_ids_are_rejected(user_id: str) -> None:
    with pytest.raises(ValidationError):
        SlackConfig(allowed_user_id=user_id)


def test_sheet_id_and_tab_are_required() -> None:
    with pytest.raises(ValidationError):
        SheetsConfig(sheet_id="abc")
    with pytest.raises(ValidationError):
        SheetsConfig(tab="Expenses")


def test_blank_fallback_category_is_rejected() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        SheetsConfig(sheet_id="a", tab="b", fallback_categories=["Food", " "])


def test_fallback_categories_are_stripped() -> None:
    sheets = SheetsConfig(sheet_id="a", tab="b", fallback_categories=[" Food "])
    assert sheets.fallback_categories == ["Food"]


def test_model_path_expands_home() -> None:
    assert SttConfig(model_path="~/m.bin").model_path == Path.home() / "m.bin"


@pytest.mark.parametrize("value", ["", "   ", None, 5])
def test_model_path_must_be_a_non_empty_string(value: object) -> None:
    with pytest.raises(ValidationError, match="whisper.cpp"):
        SttConfig(model_path=value)


@pytest.mark.parametrize("model", [ExtractConfig, DedupeConfig])
def test_unknown_keys_are_rejected(model: type) -> None:
    with pytest.raises(ValidationError):
        model(typo=1)


def test_numeric_limits() -> None:
    with pytest.raises(ValidationError):
        DedupeConfig(retention_days=0)
    with pytest.raises(ValidationError):
        ExtractConfig(example_rows=-1)
