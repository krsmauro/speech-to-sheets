from pathlib import Path

import pytest

from speech_to_sheets.stt import convert


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    recorded: list[tuple] = []
    monkeypatch.setattr(convert, "run_tool", lambda *args: recorded.append(args) or "")
    return recorded


def value_after(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


def test_builds_a_16khz_mono_pcm_wav_command(calls: list[tuple]) -> None:
    target = convert.to_wav(Path("/in/note.m4a"), Path("/out/voice.wav"), "/bin/ffmpeg", 30)
    command, timeout, setting = calls[0]
    assert target == Path("/out/voice.wav")
    assert command[0] == "/bin/ffmpeg"
    assert "-nostdin" in command and "-vn" in command
    assert value_after(command, "-i") == "/in/note.m4a"
    assert value_after(command, "-ar") == "16000"
    assert value_after(command, "-ac") == "1"
    assert value_after(command, "-c:a") == "pcm_s16le"
    assert command[-1] == "/out/voice.wav"
    assert (timeout, setting) == (30, "stt.ffmpeg")


def test_relative_paths_become_absolute(calls: list[tuple]) -> None:
    convert.to_wav(Path("-odd-name.m4a"), Path("out.wav"), "ffmpeg", 30)
    command = calls[0][0]
    assert value_after(command, "-i") == str(Path("-odd-name.m4a").absolute())
    assert command[-1] == str(Path("out.wav").absolute())
