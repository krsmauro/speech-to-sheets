from pathlib import Path

import pytest

from speech_to_sheets.config.sections import SttConfig
from speech_to_sheets.stt import voice_note
from speech_to_sheets.stt.errors import SttError

STT = SttConfig(model_path="/models/m.bin", ffmpeg="/bin/ffmpeg", timeout_seconds=30)


@pytest.fixture
def seen(monkeypatch: pytest.MonkeyPatch) -> dict:
    record: dict = {}

    def fake_to_wav(source: Path, target: Path, ffmpeg: str, timeout: float) -> Path:
        record.update(input=source.read_bytes(), folder=target.parent, tool=(ffmpeg, timeout))
        target.write_bytes(b"wav")
        return target

    monkeypatch.setattr(voice_note, "to_wav", fake_to_wav)
    return record


def test_converts_then_transcribes_and_deletes_the_audio(
    monkeypatch: pytest.MonkeyPatch, seen: dict
) -> None:
    monkeypatch.setattr(voice_note, "transcribe", lambda wav, stt: f"heard {wav.read_bytes()!r}")
    assert voice_note.transcribe_voice_note(b"note-bytes", STT) == "heard b'wav'"
    assert seen["input"] == b"note-bytes"
    assert seen["tool"] == ("/bin/ffmpeg", 30)
    assert not seen["folder"].exists()


def test_audio_is_deleted_when_transcription_fails(
    monkeypatch: pytest.MonkeyPatch, seen: dict
) -> None:
    def failing(wav: Path, stt: SttConfig) -> str:
        raise SttError("boom")

    monkeypatch.setattr(voice_note, "transcribe", failing)
    with pytest.raises(SttError):
        voice_note.transcribe_voice_note(b"note-bytes", STT)
    assert not seen["folder"].exists()
