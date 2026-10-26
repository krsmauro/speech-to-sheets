import sqlite3
import time
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from speech_to_sheets.dedupe.errors import DedupeError

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('pending', 'done', 'failed')),
    sheet_row INTEGER,
    created_at REAL NOT NULL
)
"""


class DedupeStore:
    """Remembers which Slack messages were already handled, so a repeat never adds a row.

    Mark-first: claim a message before doing anything, then finish or fail it. A message is
    never retried automatically. Only message IDs and row numbers are stored, no content.
    """

    def __init__(self, path: Path, clock: Callable[[], float] = time.time) -> None:
        self.path = path
        self.clock = clock
        with self.transaction() as db:
            db.execute(SCHEMA)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """A short connection per operation: Slack runs handlers on several threads, and
        SQLite's file lock keeps each operation atomic. Commits on success."""
        try:
            with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
                yield db
        except sqlite3.Error as error:
            raise DedupeError(f"dedupe store {self.path} (dedupe.path): {error}") from None

    def claim(self, message_id: str) -> bool:
        """True the first time a message is seen; False for every repeat."""
        if not message_id:
            raise ValueError("message_id must not be empty")
        with self.transaction() as db:
            cursor = db.execute(
                "INSERT INTO messages (message_id, status, created_at) VALUES (?, 'pending', ?)"
                " ON CONFLICT (message_id) DO NOTHING",
                (message_id, self.clock()),
            )
        return cursor.rowcount == 1

    def finish(self, message_id: str, row: int) -> None:
        """The entry is in the sheet at this row."""
        self._close(message_id, "done", row)

    def fail(self, message_id: str) -> None:
        """Handling stopped with an error; the user resends if they want it logged."""
        self._close(message_id, "failed", None)

    def _close(self, message_id: str, status: str, row: int | None) -> None:
        with self.transaction() as db:
            cursor = db.execute(
                "UPDATE messages SET status = ?, sheet_row = ?"
                " WHERE message_id = ? AND status = 'pending'",
                (status, row, message_id),
            )
        if cursor.rowcount != 1:
            raise DedupeError(f"message {message_id} is not pending, so it cannot be {status}")
