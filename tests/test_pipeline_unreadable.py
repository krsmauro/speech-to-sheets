from pathlib import Path

import pytest

from speech_to_sheets.pipeline import texts
from tests.pipeline_world import MARKET, PHOTO_URL, VOICE_URL, World, photo, voice

PDF = {"mimetype": "application/pdf", "url_private_download": "https://files.slack.com/a.pdf"}


@pytest.mark.parametrize(
    ("files", "content", "expected"),
    [
        ((voice(),), {VOICE_URL: None}, texts.NO_SPEECH),
        ((photo(),), {PHOTO_URL: None}, texts.UNREADABLE_PHOTO),
        ((PDF,), {}, texts.UNSUPPORTED_FILE),
        ((), {}, texts.NOTHING_TO_READ),
    ],
)
def test_nothing_to_read_gets_an_answer_without_calling_claude(
    tmp_path: Path, files: tuple, content: dict, expected: str
) -> None:
    world = World(tmp_path, MARKET, files=content)
    event = world.send("  ", files=files)
    assert world.replies == [expected]
    assert world.claude.calls == []
    assert world.new_rows() == []
    assert world.status(event) == ("pending", None)  # claimed, nothing logged


def test_a_silent_voice_note_with_text_still_uses_the_text(tmp_path: Path) -> None:
    world = World(tmp_path, MARKET, files={VOICE_URL: None})
    world.send("market 12.50", files=(voice(),))
    assert world.conversation() == "Conversation, oldest first:\nUser: market 12.50"
    assert world.replies[0].startswith("Logged in row 4:")
