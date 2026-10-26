from slack_sdk import WebClient

from speech_to_sheets.slack.errors import slack_errors
from speech_to_sheets.slack.text import escape


def post_reply(client: WebClient, channel: str, thread_ts: str, text: str) -> str:
    """Reply in the message's thread, so each expense keeps its own conversation. The text is
    plain: a description such as AT&T or <none> shows as written. Returns the reply's ts."""
    with slack_errors("replying in Slack"):
        response = client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=escape(text))
    return response.get("ts", "")
