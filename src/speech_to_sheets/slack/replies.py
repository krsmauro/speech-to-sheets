from slack_sdk import WebClient

from speech_to_sheets.slack.errors import slack_errors


def post_reply(client: WebClient, channel: str, thread_ts: str, text: str) -> str:
    """Reply in the message's thread, so each expense keeps its own conversation. Returns
    the reply's ts."""
    with slack_errors("replying in Slack"):
        response = client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=text)
    return response.get("ts", "")
