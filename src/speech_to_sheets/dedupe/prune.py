from speech_to_sheets.dedupe.store import DedupeStore

SECONDS_PER_DAY = 24 * 60 * 60


def prune(store: DedupeStore, older_than_days: int) -> int:
    """Delete entries older than the retention period, whatever their status.

    Run once at startup. Returns how many were deleted. A pruned message would be handled
    again if Slack delivered it again, so catch-up must never look back this far.
    """
    if older_than_days < 1:
        raise ValueError("older_than_days must be at least 1")
    cutoff = store.clock() - older_than_days * SECONDS_PER_DAY
    with store.transaction() as db:
        return db.execute("DELETE FROM messages WHERE created_at < ?", (cutoff,)).rowcount
