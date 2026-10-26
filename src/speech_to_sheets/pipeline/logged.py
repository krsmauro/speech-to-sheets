from speech_to_sheets.dedupe.lookup import any_logged
from speech_to_sheets.dedupe.store import DedupeStore
from speech_to_sheets.pipeline.texts import LOGGED_PREFIX
from speech_to_sheets.slack.message import Message


def already_logged(thread: list[Message], store: DedupeStore) -> bool:
    """True when this thread's expense is already in the sheet, so a reply such as "thanks"
    never extracts and logs it a second time.

    Two signs, each covering a gap in the other: the dedupe store knows about a row whose
    confirmation never reached Slack, and the confirmation in the thread still counts
    after the store has pruned the entry (dedupe.retention_days).
    """
    if any(m.from_bot and m.text.startswith(LOGGED_PREFIX) for m in thread):
        return True
    return any_logged(store, [m.message_id for m in thread if not m.from_bot])
