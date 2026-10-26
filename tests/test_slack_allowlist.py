from speech_to_sheets.slack.allowlist import is_allowed
from speech_to_sheets.slack.message import Message


def message(user: str, from_bot: bool = False) -> Message:
    return Message(channel="D1", ts="1.0", user=user, text="hi", from_bot=from_bot)


def test_only_the_allowed_user() -> None:
    assert is_allowed(message("U1"), {"U1", "U2"})
    assert is_allowed(message("U2"), {"U1", "U2"})
    assert not is_allowed(message("U3"), {"U1", "U2"})


def test_never_a_bot_even_with_the_allowed_id() -> None:
    assert not is_allowed(message("U1", from_bot=True), {"U1"})


def test_an_empty_allowlist_or_user_never_matches() -> None:
    assert not is_allowed(message(""), {""})
    assert not is_allowed(message("U1"), set())
