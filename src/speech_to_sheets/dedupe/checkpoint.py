from speech_to_sheets.dedupe.store import DedupeStore

CHECKPOINT = "catch_up_checkpoint"


def read_checkpoint(store: DedupeStore) -> float | None:
    """When catch-up last looked for missed messages (seconds since 1970), None before the
    first time."""
    with store.transaction() as db:
        row = db.execute("SELECT value FROM state WHERE name = ?", (CHECKPOINT,)).fetchone()
    return None if row is None else row[0]


def save_checkpoint(store: DedupeStore, at: float) -> None:
    with store.transaction() as db:
        db.execute(
            "INSERT INTO state (name, value) VALUES (?, ?)"
            " ON CONFLICT (name) DO UPDATE SET value = excluded.value",
            (CHECKPOINT, at),
        )
