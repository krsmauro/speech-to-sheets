from pathlib import Path

from speech_to_sheets.stt.run import run_tool

SAMPLE_RATE = 16000  # what whisper.cpp expects


def to_wav(source: Path, target: Path, ffmpeg: str, timeout: float) -> Path:
    """Convert any audio or video file ffmpeg can read to 16 kHz mono 16-bit wav."""
    command = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y"]
    # Absolute paths cannot be mistaken for an option ("-x") or a protocol ("http:").
    command += ["-i", str(source.absolute()), "-vn"]
    command += ["-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(target.absolute())]
    run_tool(command, timeout, "stt.ffmpeg")
    return target
