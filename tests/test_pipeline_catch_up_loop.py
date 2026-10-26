import threading
from pathlib import Path

import pytest
from slack_sdk.errors import SlackApiError

from speech_to_sheets.dedupe.checkpoint import read_checkpoint, save_checkpoint
from speech_to_sheets.pipeline import catch_up_loop
from speech_to_sheets.pipeline.catch_up_loop import start_catch_up
from speech_to_sheets.slack.errors import SlackError
from tests.fake_dm import LATE_EVENING
from tests.pipeline_world import ALLOWED, MARKET, World


def one_round(world: World, now: float = LATE_EVENING + 3600) -> None:
    """Start the loop already told to stop, so it looks once and ends."""
    stop = threading.Event()
    stop.set()
    thread = start_catch_up(world.dm, world.services, ALLOWED, 30, stop, clock=lambda: now)
    thread.join(timeout=5)
    assert not thread.is_alive()


def failing(error: str) -> object:
    def call(**request: object) -> dict:
        needed = "channels:read,groups:read,mpim:read,im:read"  # what Slack really answers
        raise SlackApiError("failed", {"ok": False, "error": error, "needed": needed})

    return call


def test_the_first_round_runs_at_once_on_a_background_thread(tmp_path: Path) -> None:
    world = World(tmp_path, MARKET)
    save_checkpoint(world.store, LATE_EVENING)
    world.dm.send("market 12.50")
    one_round(world)
    assert world.new_rows() == [4]
    assert read_checkpoint(world.store) == LATE_EVENING + 3600


def test_a_missing_scope_stops_startup_before_any_round(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = World(tmp_path)
    monkeypatch.setattr(world.dm, "conversations_list", failing("missing_scope"))
    with pytest.raises(SlackError, match="missing_scope: add im:read to the app's bot scopes"):
        start_catch_up(world.dm, world.services, ALLOWED, 30)
    assert read_checkpoint(world.store) is None


def test_a_failed_round_is_logged_and_the_loop_goes_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    world = World(tmp_path)
    save_checkpoint(world.store, LATE_EVENING)
    monkeypatch.setattr(world.dm, "conversations_history", failing("ratelimited"))
    one_round(world)
    assert "Catch-up failed, next try in 5 minutes" in caplog.text
    assert read_checkpoint(world.store) == LATE_EVENING


def test_a_bug_in_a_round_is_logged_with_its_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    world = World(tmp_path)

    def broken(*args: object) -> int:
        raise RuntimeError("bug")

    monkeypatch.setattr(catch_up_loop, "catch_up", broken)
    one_round(world)
    assert "Catch-up: unexpected error" in caplog.text
    assert "RuntimeError: bug" in caplog.text
