import shutil

from speech_to_sheets.config.sections import SttConfig
from speech_to_sheets.stt.errors import SttError


def check_stt(stt: SttConfig) -> None:
    """Fail fast at startup when a tool or the model is missing, listing every problem."""
    tools = {"stt.whisper_cli": stt.whisper_cli, "stt.ffmpeg": stt.ffmpeg}
    problems = [
        f"{setting}: command not found: {command}"
        for setting, command in tools.items()
        if shutil.which(command) is None
    ]
    if not stt.model_path.is_file():
        problems.append(f"stt.model_path: no such file: {stt.model_path}")
    if problems:
        lines = "\n".join(f"  - {problem}" for problem in problems)
        raise SttError(f"Speech-to-text is not ready:\n{lines}")
