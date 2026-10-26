import pytest
from slack_sdk.errors import SlackApiError

from speech_to_sheets.slack.errors import SlackError, slack_errors
from speech_to_sheets.slack.replies import post_reply
from tests.fake_slack import FakeSlack


def test_replies_in_the_thread() -> None:
    slack = FakeSlack()
    assert post_reply(slack, "D1", "100.1", "Logged in row 5") == "9.1"
    assert slack.posts == [{"channel": "D1", "thread_ts": "100.1", "text": "Logged in row 5"}]


def test_a_missing_scope_says_which_one_to_add() -> None:
    with pytest.raises(SlackError, match="missing_scope: add chat:write .* reinstall the app"):
        post_reply(FakeSlack(error="missing_scope"), "D1", "1", "hi")


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("invalid_auth", "token was rejected; copy it again"),
        ("ratelimited", "try again in a minute"),
        ("channel_not_found", "Slack API error channel_not_found"),
    ],
)
def test_known_error_codes_get_a_hint(code: str, expected: str) -> None:
    with pytest.raises(SlackError, match=expected), slack_errors("replying"):
        raise SlackApiError("failed", {"ok": False, "error": code})


def test_network_errors() -> None:
    with (
        pytest.raises(SlackError, match="replying: could not reach Slack"),
        slack_errors("replying"),
    ):
        raise TimeoutError("timed out")


def test_an_error_without_a_response_body() -> None:
    with pytest.raises(SlackError, match="unknown_error"), slack_errors("replying"):
        raise SlackApiError("failed", None)
