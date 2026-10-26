from dataclasses import dataclass

import gspread

from speech_to_sheets.config.sections import SheetsConfig
from speech_to_sheets.extract.inputs import ExampleRow
from speech_to_sheets.sheets.categories import read_categories
from speech_to_sheets.sheets.examples import read_examples
from speech_to_sheets.sheets.schema import Layout, read_layout


@dataclass(frozen=True)
class SheetContext:
    """What one message needs from the sheet: where the columns are, the categories, and
    the last rows as examples for Claude."""

    layout: Layout
    categories: list[str]
    examples: list[ExampleRow]


def read_context(worksheet: gspread.Worksheet, sheets: SheetsConfig, rows: int) -> SheetContext:
    """Read fresh for every message, so moved columns or new categories work at once."""
    layout = read_layout(worksheet, sheets.columns)
    categories = read_categories(worksheet, layout.category, sheets.fallback_categories)
    shown = read_examples(worksheet, layout, rows)
    examples = [ExampleRow(r.date, r.amount, r.category, r.description) for r in shown]
    return SheetContext(layout, categories, examples)
