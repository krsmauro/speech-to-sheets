from pathlib import Path

from speech_to_sheets.dedupe.lookup import any_logged, unseen
from speech_to_sheets.dedupe.store import DedupeStore


def test_only_a_done_message_counts_as_logged(tmp_path: Path) -> None:
    store = DedupeStore(tmp_path / "dedupe.sqlite")
    for message_id in ("D1:1", "D1:2", "D1:3"):
        store.claim(message_id)
    store.fail("D1:2")
    assert not any_logged(store, ["D1:1", "D1:2", "D1:9"]), "pending, failed or unknown"
    store.finish("D1:3", 7)
    assert any_logged(store, ["D1:1", "D1:3"])
    assert not any_logged(store, [])


def test_unseen_lists_only_messages_never_claimed(tmp_path: Path) -> None:
    store = DedupeStore(tmp_path / "dedupe.sqlite")
    store.claim("D1:1")
    store.claim("D1:2")
    store.fail("D1:2")
    assert unseen(store, ["D1:1", "D1:2", "D1:3"]) == {"D1:3"}, "pending and failed were seen"
    assert unseen(store, []) == set()
