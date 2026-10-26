import logging
from pathlib import Path

import anthropic
import httpx2
import pytest
import requests

from speech_to_sheets.pipeline import handle_message, log_entry, texts
from speech_to_sheets.sheets.errors import SheetsError
from tests.pipeline_world import MARKET, World

OFFLINE = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://x"))


def test_a_write_failure_says_to_check_the_sheet_and_never_confirms(tmp_path: Path) -> None:
    world = World(tmp_path, MARKET)

    def timed_out(body: dict) -> dict:
        raise requests.Timeout()

    world.sheet.spreadsheet.batch_update = timed_out
    event = world.send("market 12.50")
    [reply] = world.replies
    assert reply.startswith("Writing to the sheet failed: writing row 4: could not reach Google")
    assert "check the sheet before trying again" in reply
    assert texts.LOGGED_PREFIX not in reply
    assert world.status(event) == ("failed", None)


def test_an_error_before_writing_can_be_retried_in_the_thread(tmp_path: Path) -> None:
    world = World(tmp_path, OFFLINE, MARKET)
    first = world.send("market 12.50")
    [reply] = world.replies
    assert reply == (
        "Not logged: could not reach the Anthropic API (network problem or timeout)\n"
        "Reply here to try again."
    )
    assert world.status(first) == ("failed", None)
    world.send("try again", reply_to=first)
    assert world.replies[-1].startswith("Logged in row 4:")


def test_a_failed_read_back_still_says_the_row_is_logged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unreadable(*args: object) -> None:
        raise SheetsError("reading rows 4 to 4: could not reach Google Sheets")

    monkeypatch.setattr(log_entry, "read_row", unreadable)
    world = World(tmp_path, MARKET)
    event = world.send("market 12.50")
    [reply] = world.replies
    assert reply == (
        "Logged in row 4, but I could not read it back to show it: reading rows 4 to 4:"
        " could not reach Google Sheets"
    )
    assert world.status(event) == ("done", 4)


def test_a_bug_is_logged_in_full_and_still_answered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def broken(*args: object) -> None:
        raise KeyError("a bug")

    monkeypatch.setattr(handle_message, "bundle", broken)
    world = World(tmp_path, MARKET)
    with caplog.at_level(logging.ERROR):
        event = world.send("market 12.50")
    assert world.replies == [texts.UNEXPECTED]
    assert world.status(event) == ("failed", None)
    assert "Traceback" in caplog.text
    assert "KeyError" in caplog.text


def test_a_reply_that_cannot_be_posted_is_logged_without_the_text(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    world = World(tmp_path, MARKET)
    world.dm.failing_posts = True
    with caplog.at_level(logging.INFO):
        event = world.send("secret market 12.50")
    assert world.status(event) == ("done", 4)
    assert "could not reply: replying in Slack: Slack API error ratelimited" in caplog.text
    assert "secret" not in caplog.text
    assert "Market" not in caplog.text
