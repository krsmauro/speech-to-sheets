from pathlib import Path

import pytest
from slack_sdk.errors import SlackApiError

from speech_to_sheets.dedupe.checkpoint import read_checkpoint, save_checkpoint
from speech_to_sheets.slack.errors import SlackError
from tests.catch_up_world import DAY, HOUR, look
from tests.fake_dm import LATE_EVENING
from tests.pipeline_world import MARKET, World


def test_a_message_just_before_the_last_look_is_not_missed(tmp_path: Path) -> None:
    world = World(tmp_path, MARKET)
    save_checkpoint(world.store, LATE_EVENING + HOUR)
    late = world.dm.send("market 12.50", at=LATE_EVENING + HOUR - 60)  # listed late by Slack
    assert look(world, LATE_EVENING + 2 * HOUR) == 1
    assert world.status(late) == ("done", 4)


def test_after_a_long_time_off_only_messages_within_retention_are_handled(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    world = World(tmp_path, MARKET)
    save_checkpoint(world.store, LATE_EVENING)
    too_old = world.dm.send("taxi 8", at=LATE_EVENING + DAY)  # its dedupe entry may be pruned
    recent = world.dm.send("market 12.50", at=LATE_EVENING + 35 * DAY)
    assert look(world, LATE_EVENING + 36 * DAY) == 1
    assert world.status(too_old) is None
    assert world.status(recent) == ("done", 4)
    assert "older messages are not caught up" in caplog.text


def test_a_channel_with_someone_not_on_the_list_is_not_read(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.dm.owner = "U9"
    save_checkpoint(world.store, LATE_EVENING)
    world.dm.send("market 12.50", user="U9")
    assert look(world, LATE_EVENING + HOUR) == 0
    assert world.claude.calls == []


def test_a_failed_look_keeps_the_checkpoint_so_the_next_one_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = World(tmp_path)
    save_checkpoint(world.store, LATE_EVENING)

    def offline(**request: object) -> dict:
        raise SlackApiError("failed", {"ok": False, "error": "ratelimited"})

    monkeypatch.setattr(world.dm, "conversations_history", offline)
    with pytest.raises(SlackError, match="reading the bot's direct messages"):
        look(world, LATE_EVENING + HOUR)
    assert read_checkpoint(world.store) == LATE_EVENING
