from typing import Protocol

from speech_to_sheets.config.sections import SttConfig
from speech_to_sheets.extract.inputs import Image
from speech_to_sheets.slack.files import download
from speech_to_sheets.slack.images import image_for_claude
from speech_to_sheets.slack.message import SlackFile
from speech_to_sheets.stt.voice_note import transcribe_voice_note


class FileReader(Protocol):
    """Turns a Slack file into what Claude can read. Tests pass a fake."""

    def transcript(self, file: SlackFile) -> str | None:
        """The voice note as text; None when no speech was found."""

    def image(self, file: SlackFile) -> Image | None:
        """The photo in a format Claude accepts; None when no version of it fits."""


class SlackFileReader:
    """Downloads files with the bot token: voice notes go through whisper, photos are checked
    for a format and size the Anthropic API accepts."""

    def __init__(self, bot_token: str, stt: SttConfig) -> None:
        self._token = bot_token
        self._stt = stt

    def transcript(self, file: SlackFile) -> str | None:
        return transcribe_voice_note(self._download(file.url), self._stt)

    def image(self, file: SlackFile) -> Image | None:
        return image_for_claude(file, self._download)

    def _download(self, url: str) -> bytes:
        return download(url, self._token)
