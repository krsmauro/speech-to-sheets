import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from speech_to_sheets.pipeline.texts import ALREADY_LOGGED
from tests.pipeline_world import ASK_AMOUNT, MARKET, World


def test_a_question_then_a_reply_in_the_thread_logs_one_row(tmp_path: Path) -> None:
    world = World(tmp_path, ASK_AMOUNT, MARKET)
    first = world.send("lunch at the market")
    assert world.replies == ["How much was it?"]
    assert world.new_rows() == []
    answer = world.send("12.50", reply_to=first)
    assert world.conversation() == (
        "Conversation, oldest first:\nUser: lunch at the market\nYou: How much was it?\nUser: 12.50"
    )
    assert world.replies[-1] == "Logged in row 4: 14/1/2025 | $12.50 | Food | Market"
    assert world.new_rows() == [4]
    assert world.status(first) == ("pending", None)  # claimed, nothing logged from it alone
    assert world.status(answer) == ("done", 4)


def test_a_reply_after_the_confirmation_logs_nothing(tmp_path: Path) -> None:
    world = World(tmp_path, MARKET)
    first = world.send("market 12.50")
    world.send("thanks!", reply_to=first)
    assert world.replies[-1] == ALREADY_LOGGED
    assert len(world.claude.calls) == 1
    assert world.new_rows() == [4]


def test_two_quick_replies_in_one_thread_log_one_row(tmp_path: Path) -> None:
    world = World(tmp_path, ASK_AMOUNT, MARKET)
    first = world.send("lunch")
    replies = [world.dm.send("12.50", reply_to=first), world.dm.send("market", reply_to=first)]
    answer = world.claude.create
    # Claude is slow, so without one-at-a-time both replies read the thread before either writes.
    world.claude.create = lambda **call: time.sleep(0.05) or answer(**call)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(world.deliver, replies))
    assert world.new_rows() == [4]
    logged, second = world.replies[1:]
    assert logged.startswith("Logged in row 4:")
    assert second == ALREADY_LOGGED


def test_a_logged_thread_without_its_confirmation_still_logs_nothing(tmp_path: Path) -> None:
    # The row was written but the confirmation never reached Slack; the store remembers.
    world = World(tmp_path, MARKET)
    world.dm.failing_posts = True
    first = world.send("market 12.50")
    world.dm.failing_posts = False
    assert world.replies == []
    world.send("did you get this?", reply_to=first)
    assert world.replies == [ALREADY_LOGGED]
    assert world.new_rows() == [4]


def test_the_same_event_twice_is_handled_once(tmp_path: Path) -> None:
    world = World(tmp_path, MARKET)
    event = world.send("market 12.50")
    world.deliver(event)  # Slack redelivers it, for example after a reconnect
    assert len(world.replies) == 1
    assert len(world.claude.calls) == 1
    assert world.new_rows() == [4]


@pytest.mark.parametrize("user", ["U9", ""])
def test_someone_not_on_the_list_is_ignored(tmp_path: Path, user: str) -> None:
    world = World(tmp_path, MARKET)
    event = world.send("market 12.50", user=user)
    assert world.replies == []
    assert world.claude.calls == []
    assert world.new_rows() == []
    assert world.status(event) is None, "not even claimed"


def test_the_second_listed_person_can_log_too(tmp_path: Path) -> None:
    world = World(tmp_path, MARKET)
    world.send("market 12.50", user="U2")
    assert world.replies[0].startswith("Logged in row 4:")


def test_a_reply_slack_does_not_list_yet_is_still_read(tmp_path: Path) -> None:
    world = World(tmp_path, ASK_AMOUNT, MARKET)
    first = world.send("lunch at the market")
    answer = world.dm.send("12.50", reply_to=first)
    world.dm.messages.remove(answer)  # conversations.replies lags behind the event
    world.deliver(answer)
    assert world.conversation().endswith("You: How much was it?\nUser: 12.50")
    assert world.new_rows() == [4]
