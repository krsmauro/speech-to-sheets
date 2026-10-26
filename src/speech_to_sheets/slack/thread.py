from decimal import Decimal

from slack_sdk import WebClient

from speech_to_sheets.slack.message import Message, parse_message
from speech_to_sheets.slack.pages import pages


def read_thread(client: WebClient, channel: str, thread_ts: str) -> list[Message]:
    """Every message of a thread, oldest first, the bot's own replies included (marked
    from_bot). Re-read on each reply, so the bot keeps no conversation state."""
    messages: list[Message] = []
    replies = pages(
        client.conversations_replies, "reading the Slack thread", channel=channel, ts=thread_ts
    )
    for response in replies:
        for raw in response.get("messages", []):
            message = parse_message(raw, channel)
            if message is not None:
                messages.append(message)
    unique = {message.ts: message for message in messages}  # pages may repeat the parent
    return sorted(unique.values(), key=lambda message: Decimal(message.ts))
