import pytest

from speech_to_sheets.extract.errors import ExtractError
from speech_to_sheets.pipeline import texts
from speech_to_sheets.sheets.errors import SheetsError, WriteError
from speech_to_sheets.sheets.rows import DisplayedRow
from speech_to_sheets.stt.errors import SttError

ROW = DisplayedRow(4, "14/1/2025", "$12.50", "Food", "Market")
FIXED = [
    texts.ALREADY_LOGGED,
    texts.NO_SPEECH,
    texts.UNREADABLE_PHOTO,
    texts.UNSUPPORTED_FILE,
    texts.NOTHING_TO_READ,
    texts.UNEXPECTED,
]


def test_the_confirmation_lists_the_row_as_displayed() -> None:
    assert texts.logged(ROW) == "Logged in row 4: 14/1/2025 | $12.50 | Food | Market"


def test_both_logged_texts_start_with_the_prefix_the_thread_check_looks_for() -> None:
    assert texts.logged(ROW).startswith(texts.LOGGED_PREFIX)
    assert texts.logged_unread(4, SheetsError("timeout")).startswith(texts.LOGGED_PREFIX)


@pytest.mark.parametrize("error", [WriteError("w"), SheetsError("s"), ExtractError("e")])
def test_no_failure_looks_like_a_confirmation(error: Exception) -> None:
    assert not texts.failed(error).startswith(texts.LOGGED_PREFIX)


@pytest.mark.parametrize("text", FIXED)
def test_no_fixed_reply_looks_like_a_confirmation(text: str) -> None:
    assert not text.startswith(texts.LOGGED_PREFIX)


def test_only_a_failed_write_says_to_check_the_sheet() -> None:
    assert "check the sheet" in texts.failed(WriteError("writing row 4: timeout"))
    assert "check the sheet" not in texts.failed(SheetsError("reading the headers in row 1"))
    assert texts.failed(SttError("ffmpeg failed")) == (
        "Not logged: ffmpeg failed\nReply here to try again."
    )
