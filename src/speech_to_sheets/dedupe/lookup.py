from collections.abc import Collection

from speech_to_sheets.dedupe.store import DedupeStore


def any_logged(store: DedupeStore, message_ids: Collection[str]) -> bool:
    """True when one of these messages already put a row in the sheet (status done)."""
    if not message_ids:
        return False
    marks = ", ".join("?" for _ in message_ids)
    query = f"SELECT 1 FROM messages WHERE status = 'done' AND message_id IN ({marks}) LIMIT 1"
    with store.transaction() as db:
        return db.execute(query, list(message_ids)).fetchone() is not None


def unseen(store: DedupeStore, message_ids: Collection[str]) -> set[str]:
    """The message IDs the store never claimed: messages the bot has not handled yet."""
    if not message_ids:
        return set()
    marks = ", ".join("?" for _ in message_ids)
    query = f"SELECT message_id FROM messages WHERE message_id IN ({marks})"
    with store.transaction() as db:
        seen = {row[0] for row in db.execute(query, list(message_ids))}
    return set(message_ids) - seen
