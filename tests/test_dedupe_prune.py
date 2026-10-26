from pathlib import Path

import pytest

from speech_to_sheets.dedupe.prune import SECONDS_PER_DAY, prune
from speech_to_sheets.dedupe.store import DedupeStore

DAY = SECONDS_PER_DAY


class Clock:
    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def test_deletes_only_entries_older_than_the_retention(tmp_path: Path) -> None:
    clock = Clock(0.0)
    store = DedupeStore(tmp_path / "dedupe.sqlite", clock=clock)
    store.claim("old-done")
    store.finish("old-done", 2)
    store.claim("old-pending")
    clock.now = 25 * DAY
    store.claim("recent")
    clock.now = 30 * DAY + 1
    assert prune(store, older_than_days=30) == 2
    assert store.claim("recent") is False, "recent entries are kept"
    assert store.claim("old-done") is True, "a pruned message counts as new again"


def test_an_entry_exactly_at_the_limit_is_kept(tmp_path: Path) -> None:
    clock = Clock(0.0)
    store = DedupeStore(tmp_path / "dedupe.sqlite", clock=clock)
    store.claim("edge")
    clock.now = 30 * DAY
    assert prune(store, older_than_days=30) == 0


def test_empty_store_prunes_nothing(tmp_path: Path) -> None:
    assert prune(DedupeStore(tmp_path / "dedupe.sqlite"), older_than_days=30) == 0


def test_retention_must_be_at_least_a_day(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        prune(DedupeStore(tmp_path / "dedupe.sqlite"), older_than_days=0)
