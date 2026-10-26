import sqlite3
from pathlib import Path

from speech_to_sheets.dedupe.checkpoint import read_checkpoint, save_checkpoint
from speech_to_sheets.dedupe.store import DedupeStore


def test_none_until_saved_then_the_latest_value_across_restarts(tmp_path: Path) -> None:
    store = DedupeStore(tmp_path / "dedupe.sqlite")
    assert read_checkpoint(store) is None
    save_checkpoint(store, 100.5)
    save_checkpoint(store, 200.25)
    assert read_checkpoint(DedupeStore(tmp_path / "dedupe.sqlite")) == 200.25


def test_a_store_made_before_catch_up_existed_gets_the_new_table(tmp_path: Path) -> None:
    path = tmp_path / "dedupe.sqlite"
    with sqlite3.connect(path) as db:  # the schema of the first release
        db.execute(
            "CREATE TABLE messages (message_id TEXT PRIMARY KEY, status TEXT NOT NULL,"
            " sheet_row INTEGER, created_at REAL NOT NULL)"
        )
        db.execute("INSERT INTO messages VALUES ('D1:1', 'done', 4, 1.0)")
    store = DedupeStore(path)
    save_checkpoint(store, 300.0)
    assert read_checkpoint(store) == 300.0
    assert not store.claim("D1:1"), "earlier entries are kept"
