from collections.abc import Collection

from speech_to_sheets.slack.message import Message


def is_allowed(message: Message, allowed_user_ids: Collection[str]) -> bool:
    """Only the configured people may write to the sheet. Bots, including this one, never."""
    return not message.from_bot and bool(message.user) and message.user in allowed_user_ids
