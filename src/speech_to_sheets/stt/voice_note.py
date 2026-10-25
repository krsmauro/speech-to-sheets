from pathlib import Path
from tempfile import TemporaryDirectory

from speech_to_sheets.config.sections import SttConfig
from speech_to_sheets.stt.convert import to_wav
from speech_to_sheets.stt.whisper import transcribe


def transcribe_voice_note(audio: bytes, stt: SttConfig) -> str | None:
    """Transcribe a downloaded voice note in any format ffmpeg reads; ffmpeg detects the format.

    Returns None when no speech was found. Audio is personal data, so it only lives in a
    private temporary folder that is deleted afterwards, even when a step fails.
    """
    with TemporaryDirectory(prefix="speech-to-sheets-") as folder:
        source = Path(folder) / "voice-note"
        source.write_bytes(audio)
        wav = to_wav(source, Path(folder) / "voice.wav", stt.ffmpeg, stt.timeout_seconds)
        return transcribe(wav, stt)
