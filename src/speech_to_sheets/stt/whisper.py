from pathlib import Path

from speech_to_sheets.config.sections import SttConfig
from speech_to_sheets.stt.errors import SttError
from speech_to_sheets.stt.run import run_tool
from speech_to_sheets.stt.transcript import clean_transcript


def transcribe(wav: Path, stt: SttConfig) -> str | None:
    """Transcribe a 16 kHz mono wav with whisper-cli. Returns None when no speech was found."""
    if not stt.model_path.is_file():
        raise SttError(f"whisper model not found at {stt.model_path}; check stt.model_path")
    # whisper-cli defaults to English, so the language is always passed explicitly.
    command = [stt.whisper_cli, "-m", str(stt.model_path), "-f", str(wav), "-nt"]
    command += ["-l", stt.language]
    return clean_transcript(run_tool(command, stt.timeout_seconds, "stt.whisper_cli"))
