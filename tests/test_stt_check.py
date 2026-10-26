import sys
from pathlib import Path

import pytest

from speech_to_sheets.config.sections import SttConfig
from speech_to_sheets.stt.check import check_stt
from speech_to_sheets.stt.errors import SttError


def test_passes_when_tools_and_model_exist(tmp_path: Path) -> None:
    model = tmp_path / "model.bin"
    model.write_bytes(b"")
    check_stt(SttConfig(whisper_cli=sys.executable, ffmpeg=sys.executable, model_path=str(model)))


def test_lists_every_problem(tmp_path: Path) -> None:
    stt = SttConfig(
        whisper_cli="no-such-whisper-for-tests",
        ffmpeg="no-such-ffmpeg-for-tests",
        model_path=str(tmp_path / "missing.bin"),
    )
    with pytest.raises(SttError) as caught:
        check_stt(stt)
    for setting in ("stt.whisper_cli", "stt.ffmpeg", "stt.model_path"):
        assert setting in str(caught.value)
