from decimal import Decimal

from slack_sdk import WebClient

from speech_to_sheets.slack.errors import slack_errors
from speech_to_sheets.slack.message import Message, parse_message

PAGE_SIZE = 200  # Slack's recommended maximum per request


def read_thread(client: WebClient, channel: str, thread_ts: str) -> list[Message]:
    """Every message of a thread, oldest first, the bot's own replies included (marked
    from_bot). Re-read on each reply, so the bot keeps no conversation state."""
    messages: list[Message] = []
    cursor = None
    while True:
        with slack_errors("reading the Slack thread"):
            response = client.conversations_replies(
                channel=channel, ts=thread_ts, cursor=cursor, limit=PAGE_SIZE
            )
        for raw in response.get("messages", []):
            message = parse_message(raw, channel)
            if message is not None:
                messages.append(message)
        cursor = (response.get("response_metadata") or {}).get("next_cursor")
        if not cursor:
            break
    unique = {message.ts: message for message in messages}  # pages may repeat the parent
    return sorted(unique.values(), key=lambda message: Decimal(message.ts))
