import pytest

from speech_to_sheets.config.sections import SttConfig
from speech_to_sheets.pipeline import files
from speech_to_sheets.pipeline.files import SlackFileReader
from speech_to_sheets.slack.message import SlackFile

STT = SttConfig(model_path="/models/m.bin")
VOICE = SlackFile("clip", "audio/mp4", "slack_audio", 1000, "https://files.slack.com/clip")
PHOTO = SlackFile("img", "image/jpeg", "", 1000, "https://files.slack.com/img")


@pytest.fixture
def downloads(monkeypatch: pytest.MonkeyPatch) -> list:
    seen = []

    def fake_download(url: str, token: str) -> bytes:
        seen.append((url, token))
        return b"\xff\xd8\xff bytes"

    monkeypatch.setattr(files, "download", fake_download)
    return seen


def test_a_voice_note_is_downloaded_with_the_bot_token_and_transcribed(
    monkeypatch: pytest.MonkeyPatch, downloads: list
) -> None:
    def fake_transcribe(audio: bytes, stt: SttConfig) -> str:
        return f"{len(audio)} bytes with {stt.model_path}"

    monkeypatch.setattr(files, "transcribe_voice_note", fake_transcribe)
    assert SlackFileReader("xoxb-1", STT).transcript(VOICE) == "9 bytes with /models/m.bin"
    assert downloads == [(VOICE.url, "xoxb-1")]


def test_a_photo_is_downloaded_and_checked_for_a_format_claude_accepts(downloads: list) -> None:
    image = SlackFileReader("xoxb-1", STT).image(PHOTO)
    assert image.media_type == "image/jpeg"
    assert downloads == [(PHOTO.url, "xoxb-1")]


def test_the_token_does_not_show_in_the_reader_repr() -> None:
    assert "xoxb" not in repr(SlackFileReader("xoxb-secret", STT))
