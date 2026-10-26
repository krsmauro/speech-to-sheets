from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from speech_to_sheets.dedupe.errors import DedupeError
from speech_to_sheets.dedupe.store import DedupeStore


@pytest.fixture
def store(tmp_path: Path) -> DedupeStore:
    return DedupeStore(tmp_path / "dedupe.sqlite", clock=lambda: 1000.0)


def saved(store: DedupeStore, message_id: str) -> tuple | None:
    with store.transaction() as db:
        query = "SELECT status, sheet_row, created_at FROM messages WHERE message_id = ?"
        return db.execute(query, (message_id,)).fetchone()


def test_first_claim_wins_and_repeats_lose(store: DedupeStore) -> None:
    assert store.claim("C1-1700000000.000100") is True
    assert store.claim("C1-1700000000.000100") is False
    assert store.claim("C1-1700000000.000200") is True
    assert saved(store, "C1-1700000000.000100") == ("pending", None, 1000.0)


def test_finish_stores_the_row_and_the_message_stays_claimed(store: DedupeStore) -> None:
    store.claim("m1")
    store.finish("m1", 224)
    assert saved(store, "m1") == ("done", 224, 1000.0)
    assert store.claim("m1") is False


def test_fail_is_final_and_never_retried(store: DedupeStore) -> None:
    store.claim("m1")
    store.fail("m1")
    assert saved(store, "m1") == ("failed", None, 1000.0)
    assert store.claim("m1") is False


@pytest.mark.parametrize("close", ["finish", "fail"])
def test_only_a_pending_message_can_be_closed(store: DedupeStore, close: str) -> None:
    def run(message_id: str) -> None:
        if close == "finish":
            store.finish(message_id, 5)
        else:
            store.fail(message_id)

    with pytest.raises(DedupeError, match="never-claimed is not pending"):
        run("never-claimed")
    store.claim("m1")
    store.finish("m1", 7)
    with pytest.raises(DedupeError, match="not pending"):
        run("m1")
    assert saved(store, "m1") == ("done", 7, 1000.0), "a done entry is never overwritten"


def test_claims_survive_a_restart(tmp_path: Path) -> None:
    path = tmp_path / "dedupe.sqlite"
    first = DedupeStore(path)
    first.claim("m1")
    first.finish("m1", 3)
    assert DedupeStore(path).claim("m1") is False


def test_concurrent_claims_of_one_message_have_one_winner(store: DedupeStore) -> None:
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: store.claim("same"), range(32)))
    assert results.count(True) == 1


def test_empty_message_id_is_rejected(store: DedupeStore) -> None:
    with pytest.raises(ValueError):
        store.claim("")


def test_unusable_path_names_the_config_key(tmp_path: Path) -> None:
    with pytest.raises(DedupeError, match=r"dedupe\.path"):
        DedupeStore(tmp_path / "missing-folder" / "dedupe.sqlite")
