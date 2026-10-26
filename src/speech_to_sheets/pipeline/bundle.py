import logging
from dataclasses import dataclass, field

from speech_to_sheets.extract.inputs import ExtractionInput, Image, Turn
from speech_to_sheets.pipeline import texts
from speech_to_sheets.pipeline.files import FileReader
from speech_to_sheets.slack.message import Message

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Bundle:
    request: ExtractionInput
    unusable: str | None = None  # set when the newest message gave nothing to read: why


@dataclass
class _Parts:
    turns: list[Turn] = field(default_factory=list)
    images: list[Image] = field(default_factory=list)
    problem: str | None = None


def bundle(thread: list[Message], newest: Message, files: FileReader) -> Bundle:
    """The whole thread, oldest first, as one extraction input: texts, voice note transcripts
    and photos. Nothing is remembered between messages, so earlier voice notes are
    transcribed again. When the newest message gives nothing to read (a silent voice note,
    a PDF), the reply says why and Claude is not called."""
    newest_parts = _read(newest, files)
    if not newest_parts.turns and not newest_parts.images:
        return Bundle(ExtractionInput(), newest_parts.problem or texts.NOTHING_TO_READ)
    turns: list[Turn] = []
    images: list[Image] = []
    for message in thread:
        parts = newest_parts if message.ts == newest.ts else _read(message, files)
        turns += parts.turns
        images += parts.images
    return Bundle(ExtractionInput(tuple(turns), tuple(images)))


def _read(message: Message, files: FileReader) -> _Parts:
    text = message.text.strip()
    if message.from_bot:
        return _Parts([Turn("bot", text)] if text else [])
    parts = _Parts([Turn("user", text)] if text else [])
    for file in message.files:
        if file.is_voice:
            transcript = files.transcript(file)
            if transcript:
                parts.turns.append(Turn("user", transcript, voice=True))
            else:
                parts.problem = texts.NO_SPEECH
        elif file.is_image:
            image = files.image(file)
            if image:
                parts.images.append(image)
            else:
                parts.problem = texts.UNREADABLE_PHOTO
        else:
            logger.info("Skipped a file of type %s", file.mimetype or "unknown")
            parts.problem = texts.UNSUPPORTED_FILE
    return parts
