from dataclasses import dataclass

import anthropic
import gspread

from speech_to_sheets.config.sections import ExtractConfig, SheetsConfig
from speech_to_sheets.dedupe.store import DedupeStore
from speech_to_sheets.pipeline.files import FileReader


@dataclass(frozen=True)
class Services:
    """Everything handling a message needs, opened once at startup (see startup.py)."""

    worksheet: gspread.Worksheet
    store: DedupeStore
    claude: anthropic.Anthropic
    files: FileReader
    sheets: SheetsConfig
    extract: ExtractConfig
    timezone: str
