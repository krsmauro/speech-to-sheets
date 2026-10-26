from pathlib import Path

import pytest

from speech_to_sheets.dedupe.store import DedupeStore
from speech_to_sheets.pipeline.logged import already_logged
from speech_to_sheets.slack.message import Message

CONFIRMATION = "Logged in row 4: 14/1/2025 | $12.50 | Food | Market"


def user(ts: str, text: str = "lunch") -> Message:
    return Message("D1", ts, "U1", text)


def bot(ts: str, text: str) -> Message:
    return Message("D1", ts, "UBOT", text, from_bot=True)


@pytest.fixture
def store(tmp_path: Path) -> DedupeStore:
    return DedupeStore(tmp_path / "dedupe.sqlite")


def test_the_bot_confirmation_in_the_thread_counts(store: DedupeStore) -> None:
    assert already_logged([user("1"), bot("2", CONFIRMATION), user("3")], store)


def test_a_done_message_in_the_store_counts_without_a_confirmation(store: DedupeStore) -> None:
    store.claim("D1:1")
    store.finish("D1:1", 4)
    assert already_logged([user("1"), user("3")], store)


@pytest.mark.parametrize(
    "thread",
    [
        [user("1"), bot("2", "How much was it?")],
        [user("1"), bot("2", "Not logged: Logged in row could not be read")],
        [user("1", CONFIRMATION)],  # a person typing it is not the bot confirming it
    ],
)
def test_questions_errors_and_lookalikes_do_not_count(
    store: DedupeStore, thread: list[Message]
) -> None:
    store.claim("D1:1")  # pending: claimed, nothing written
    assert not already_logged(thread, store)
