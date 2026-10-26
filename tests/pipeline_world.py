from pathlib import Path

from speech_to_sheets.config.sections import ExtractConfig, SheetsConfig
from speech_to_sheets.dedupe.store import DedupeStore
from speech_to_sheets.extract.inputs import Image
from speech_to_sheets.pipeline.handle_message import handle_message
from speech_to_sheets.pipeline.services import Services
from speech_to_sheets.slack.client import handle_event
from speech_to_sheets.slack.message import SlackFile
from tests.fake_anthropic import FakeClient, answer, reply
from tests.fake_dm import FakeDm
from tests.fake_shown_sheet import ShownWorksheet

ALLOWED = ("U1", "U2")
FIRST_NEW_ROW = 4  # the fake sheet has a header and two entries
MARKET = answer(status="complete", amount=12.5, category="Food", description="Market")
ASK_AMOUNT = answer(status="needs_info", question="How much was it?")
VOICE_URL = "https://files.slack.com/voice-1"
PHOTO_URL = "https://files.slack.com/photo-1"
RECEIPT = Image("image/jpeg", b"\xff\xd8\xff receipt")


def voice() -> dict:
    return {"mimetype": "audio/mp4", "subtype": "slack_audio", "url_private_download": VOICE_URL}


def photo() -> dict:
    return {"mimetype": "image/jpeg", "size": 1_400_000, "url_private_download": PHOTO_URL}


class FakeFiles:
    """Stands in for downloads and whisper: what each file URL holds once read."""

    def __init__(self, content: dict[str, str | Image | None]) -> None:
        self.content = content
        self.read: list[str] = []

    def transcript(self, file: SlackFile) -> str | None:
        self.read.append(file.url)
        return self.content[file.url]

    def image(self, file: SlackFile) -> Image | None:
        self.read.append(file.url)
        return self.content[file.url]


class World:
    """The bot with everything around it faked: the Slack DM, Claude (answering in the order
    given), files and whisper, and the sheet. The dedupe store is a real SQLite file."""

    def __init__(self, tmp_path: Path, *answers: object, files: dict | None = None) -> None:
        self.dm = FakeDm()
        self.sheet = ShownWorksheet()
        self.claude = FakeClient(*(a if isinstance(a, Exception) else reply(a) for a in answers))
        self.files = FakeFiles(files or {})
        self.store = DedupeStore(tmp_path / "dedupe.sqlite")
        self.services = Services(
            worksheet=self.sheet,
            store=self.store,
            claude=self.claude,
            files=self.files,
            sheets=SheetsConfig(sheet_id="sheet-1", tab="Expenses"),
            extract=ExtractConfig(),
            timezone="America/Panama",
        )

    def send(self, text: str = "", **options: object) -> dict:
        """A person sends a message; the bot handles it as the Bolt listener would."""
        event = self.dm.send(text, **options)
        self.deliver(event)
        return event

    def deliver(self, event: dict) -> None:
        handle_event(event, self.dm, ALLOWED, lambda m, c: handle_message(m, c, self.services))

    @property
    def replies(self) -> list[str]:
        return self.dm.bot_texts()

    def new_rows(self) -> list[int]:
        return sorted({row for row, _ in self.sheet.cells if row >= FIRST_NEW_ROW})

    def status(self, event: dict) -> tuple | None:
        """The dedupe store's status and row for a message, None if it was never claimed."""
        with self.store.transaction() as db:
            query = "SELECT status, sheet_row FROM messages WHERE message_id = ?"
            return db.execute(query, (f"{event['channel']}:{event['ts']}",)).fetchone()

    def conversation(self, call: int = -1) -> str:
        """The thread as Claude saw it in one call (the text block after any images)."""
        return self.claude.calls[call]["messages"][0]["content"][-1]["text"]
