import pytest

from speech_to_sheets.slack.errors import SlackError
from speech_to_sheets.slack.thread import read_thread
from tests.fake_slack import FakeSlack

ROOT = {"user": "U1", "text": "lunch", "ts": "100.000001"}
QUESTION = {
    "bot_id": "B1",
    "user": "UBOT",
    "text": "How much?",
    "ts": "100.5",
    "thread_ts": "100.000001",
}
ANSWER = {"user": "U1", "text": "12", "ts": "101.0", "thread_ts": "100.000001"}


def test_rebuilds_the_thread_oldest_first_with_the_bot_marked() -> None:
    slack = FakeSlack([{"messages": [ROOT, QUESTION, ANSWER]}])
    thread = read_thread(slack, "D1", "100.000001")
    assert [(m.text, m.from_bot) for m in thread] == [
        ("lunch", False),
        ("How much?", True),
        ("12", False),
    ]
    assert slack.reads == [{"channel": "D1", "ts": "100.000001", "cursor": None, "limit": 200}]


def test_follows_every_page_and_keeps_each_message_once() -> None:
    pages = [
        {"messages": [ROOT, QUESTION], "response_metadata": {"next_cursor": "c2"}},
        {"messages": [ROOT, ANSWER], "response_metadata": {"next_cursor": ""}},
    ]
    slack = FakeSlack(pages)
    assert [m.ts for m in read_thread(slack, "D1", "100.000001")] == [
        "100.000001",
        "100.5",
        "101.0",
    ]
    assert slack.reads[1]["cursor"] == "c2"


def test_sorts_by_time_not_by_text() -> None:
    # As text, "99.9" sorts after "100.000001"; as a time it comes first.
    earlier = {"user": "U1", "text": "x", "ts": "99.9"}
    thread = read_thread(FakeSlack([{"messages": [ROOT, earlier]}]), "D1", "1")
    assert [m.ts for m in thread] == ["99.9", "100.000001"]


def test_edits_and_deletions_in_the_thread_are_left_out() -> None:
    edited = {"subtype": "message_changed", "ts": "102.0"}
    assert len(read_thread(FakeSlack([{"messages": [ROOT, edited]}]), "D1", "1")) == 1


def test_a_slack_error_says_what_was_being_done() -> None:
    with pytest.raises(SlackError, match="reading the Slack thread: Slack API error invalid_auth"):
        read_thread(FakeSlack(error="invalid_auth"), "D1", "1")
