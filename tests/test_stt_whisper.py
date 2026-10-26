from pathlib import Path

import pytest

from speech_to_sheets.config.sections import SttConfig
from speech_to_sheets.stt import whisper
from speech_to_sheets.stt.errors import SttError


@pytest.fixture
def stt(tmp_path: Path) -> SttConfig:
    model = tmp_path / "model.bin"
    model.write_bytes(b"")
    return SttConfig(
        whisper_cli="/bin/whisper-cli", model_path=str(model), language="fr", timeout_seconds=45
    )


def fake_whisper(monkeypatch: pytest.MonkeyPatch, output: str) -> list[tuple]:
    calls: list[tuple] = []
    monkeypatch.setattr(whisper, "run_tool", lambda *args: calls.append(args) or output)
    return calls


def test_command_passes_model_file_and_configured_language(
    monkeypatch: pytest.MonkeyPatch, stt: SttConfig
) -> None:
    calls = fake_whisper(monkeypatch, "hello")
    whisper.transcribe(Path("/tmp/a.wav"), stt)
    command, timeout, setting = calls[0]
    expected = ["/bin/whisper-cli", "-m", str(stt.model_path), "-f", "/tmp/a.wav", "-nt"]
    assert command == [*expected, "-l", "fr"]
    assert (timeout, setting) == (45, "stt.whisper_cli")


def test_segments_are_joined_into_one_line(monkeypatch: pytest.MonkeyPatch, stt: SttConfig) -> None:
    fake_whisper(monkeypatch, " twenty dollars\n at the market\n")
    assert whisper.transcribe(Path("a.wav"), stt) == "twenty dollars at the market"


def test_no_speech_returns_none(monkeypatch: pytest.MonkeyPatch, stt: SttConfig) -> None:
    fake_whisper(monkeypatch, " [BLANK_AUDIO]\n")
    assert whisper.transcribe(Path("a.wav"), stt) is None


def test_missing_model_fails_before_running(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = fake_whisper(monkeypatch, "hello")
    stt = SttConfig(model_path=str(tmp_path / "missing.bin"))
    wav = Path("a.wav")
    with pytest.raises(SttError, match="stt.model_path"):
        whisper.transcribe(wav, stt)
    assert calls == []
