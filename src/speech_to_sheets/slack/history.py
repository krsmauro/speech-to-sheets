from collections.abc import Collection
from decimal import Decimal

from slack_sdk import WebClient

from speech_to_sheets.slack.message import Message, parse_message
from speech_to_sheets.slack.pages import pages
from speech_to_sheets.slack.thread import read_thread


def dm_channels(client: WebClient, allowed_user_ids: Collection[str]) -> list[str]:
    """The bot's direct message channels with the allowed people. Needs the im:read scope.
    Other people's channels are never read."""
    # Slack's error lists every scope conversations.list can use; direct messages need only
    # im:read, so the message names that one and the bot is never given channel access.
    action = "listing the bot's direct messages"
    found = pages(client.conversations_list, action, scope="im:read", types="im")
    return [
        channel["id"]
        for response in found
        for channel in response.get("channels", [])
        if channel.get("user") in allowed_user_ids
    ]


def messages_since(
    client: WebClient, channel: str, since: float, threads_since: float
) -> list[Message]:
    """Messages sent in a channel after `since`, oldest first, thread replies and the bot's
    own messages included. Slack lists a reply only under its thread's first message, so
    replies are found in threads started after `threads_since`."""
    found: dict[str, Message] = {}
    history = pages(
        client.conversations_history,
        "reading the bot's direct messages",
        channel=channel,
        oldest=f"{threads_since:.6f}",
    )
    for response in history:
        for raw in response.get("messages", []):
            message = parse_message(raw, channel)
            if message is not None and float(message.ts) > since:
                found[message.ts] = message
            if _replied_after(raw, since):
                for reply in read_thread(client, channel, raw["ts"]):
                    if float(reply.ts) > since:
                        found[reply.ts] = reply
    return sorted(found.values(), key=lambda message: Decimal(message.ts))


def _replied_after(raw: dict, since: float) -> bool:
    """A thread's first message carries its reply count and the time of its last reply."""
    if not raw.get("reply_count"):
        return False
    latest = raw.get("latest_reply")
    return latest is None or float(latest) > since  # no time given: look to be safe
