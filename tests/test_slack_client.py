import logging

import pytest
from slack_bolt import App
from slack_bolt.error import BoltError

from speech_to_sheets.slack import client
from speech_to_sheets.slack.client import build_app, handle_event
from speech_to_sheets.slack.errors import SlackError

DM = {
    "type": "message",
    "channel_type": "im",
    "channel": "D1",
    "user": "U1",
    "text": "hi",
    "ts": "1.0",
}


def handled(event: dict, allowed: tuple = ("U1", "U2")) -> list:
    seen = []
    handle_event(event, "client", allowed, lambda message, client: seen.append((message, client)))
    return seen


def test_a_direct_message_from_each_allowed_person_is_handled() -> None:
    [(message, client)] = handled(DM)
    assert (message.channel, message.user, message.text, client) == ("D1", "U1", "hi", "client")
    [(message, _)] = handled({**DM, "channel": "D2", "user": "U2"})
    assert (message.channel, message.user) == ("D2", "U2")


def test_another_user_is_ignored_and_logged_without_the_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        assert handled({**DM, "user": "U3", "text": "secret"}) == []
    assert "U3" in caplog.text and "secret" not in caplog.text


@pytest.mark.parametrize(
    "change",
    [
        {"channel_type": "channel"},
        {"bot_id": "B1"},
        {"subtype": "message_changed"},
        {"subtype": "message_deleted"},
        {"user": ""},
    ],
)
def test_channels_bots_edits_and_deletions_are_ignored(change: dict) -> None:
    assert handled({**DM, **change}) == []


def test_bot_messages_are_dropped_quietly(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        assert handled({**DM, "bot_id": "B1", "user": "UBOT"}) == []
    assert caplog.text == ""  # the bot's own replies must not fill the log with warnings


def test_an_empty_allowlist_lets_nobody_in() -> None:
    assert handled({**DM, "user": ""}, allowed=("",)) == []
    assert handled(DM, allowed=()) == []


def test_build_app_registers_a_listener_without_the_network() -> None:
    app = build_app("xoxb-test", ["U1"], lambda message, client: None, verify_token=False)
    assert isinstance(app, App)
    assert len(app._listeners) == 1


def test_a_rejected_bot_token_is_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def rejecting_app(**kwargs: object) -> None:
        raise BoltError("`token` is invalid (auth.test result: ...)")

    monkeypatch.setattr(client, "App", rejecting_app)
    with pytest.raises(SlackError, match="SLACK_BOT_TOKEN: Slack rejected it"):
        build_app("xoxb-bad", ["U1"], lambda message, client: None)
