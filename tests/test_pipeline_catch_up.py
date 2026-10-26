from pathlib import Path

from speech_to_sheets.dedupe.checkpoint import read_checkpoint, save_checkpoint
from tests.catch_up_world import HOUR, look
from tests.fake_dm import LATE_EVENING
from tests.pipeline_world import ASK_AMOUNT, MARKET, World

LOGGED_ROW_4 = "Logged in row 4: 14/1/2025 | $12.50 | Food | Market"


def test_the_first_start_only_notes_the_time(tmp_path: Path) -> None:
    world = World(tmp_path)  # Claude has no answers: any call would fail the test
    world.dm.send("market 12.50")  # sent before the bot ever ran
    assert look(world, LATE_EVENING + HOUR) == 0
    assert (world.replies, world.claude.calls) == ([], [])
    assert read_checkpoint(world.store) == LATE_EVENING + HOUR


def test_a_message_sent_while_the_bot_was_off_is_logged(tmp_path: Path) -> None:
    world = World(tmp_path, MARKET)
    save_checkpoint(world.store, LATE_EVENING)
    missed = world.dm.send("market 12.50")  # its event never reached the bot
    assert look(world, LATE_EVENING + HOUR) == 1
    assert world.replies == [LOGGED_ROW_4], "dated the day it was sent, not the day handled"
    assert world.status(missed) == ("done", 4)
    assert read_checkpoint(world.store) == LATE_EVENING + HOUR


def test_messages_already_handled_and_the_bots_replies_are_skipped(tmp_path: Path) -> None:
    world = World(tmp_path, MARKET)
    save_checkpoint(world.store, LATE_EVENING)
    world.send("market 12.50")  # handled live; the confirmation lands in its thread
    assert look(world, LATE_EVENING + HOUR) == 0
    assert len(world.claude.calls) == 1
    assert world.replies == [LOGGED_ROW_4]


def test_a_reply_to_an_earlier_question_completes_the_expense(tmp_path: Path) -> None:
    world = World(tmp_path, ASK_AMOUNT, MARKET)
    first = world.send("lunch at the market")  # handled live: the bot asks
    save_checkpoint(world.store, LATE_EVENING + HOUR)
    world.dm.send("12.50", reply_to=first, at=LATE_EVENING + 2 * HOUR)  # sent while asleep
    assert look(world, LATE_EVENING + 3 * HOUR) == 1
    assert world.replies == ["How much was it?", LOGGED_ROW_4]
    assert world.new_rows() == [4]


def test_several_missed_messages_are_handled_oldest_first(tmp_path: Path) -> None:
    world = World(tmp_path, MARKET, MARKET)
    save_checkpoint(world.store, LATE_EVENING)
    world.dm.send("market 12.50")
    world.dm.send("market again 12.50")
    assert look(world, LATE_EVENING + HOUR) == 2
    assert world.conversation(0).endswith("User: market 12.50")
    assert world.conversation(1).endswith("User: market again 12.50")
    assert world.new_rows() == [4, 5]
