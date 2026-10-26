from dataclasses import astuple, dataclass

import gspread
from gspread.utils import ValueRenderOption, rowcol_to_a1

from speech_to_sheets.sheets.errors import google_errors
from speech_to_sheets.sheets.schema import Layout


@dataclass(frozen=True)
class DisplayedRow:
    """One row as the sheet shows it, with the cells' own formatting."""

    row: int
    date: str
    amount: str
    category: str
    description: str


def last_filled_row(worksheet: gspread.Worksheet, layout: Layout) -> int:
    """The last row with something in the date column. The header counts: 1 means no entries."""
    with google_errors("finding the last entry"):
        dates = worksheet.col_values(layout.date)
    return len(dates)


def read_rows(
    worksheet: gspread.Worksheet, layout: Layout, first: int, last: int
) -> list[DisplayedRow]:
    """Rows first to last as displayed. Reads only the span of the four mapped columns."""
    columns = astuple(layout)  # date, amount, category, description: DisplayedRow's order
    left = min(columns)
    span = f"{rowcol_to_a1(first, left)}:{rowcol_to_a1(last, max(columns))}"
    with google_errors(f"reading rows {first} to {last}"):
        values = worksheet.get(span, value_render_option=ValueRenderOption.formatted)
    rows = []
    for offset in range(last - first + 1):
        # The API leaves out trailing empty rows and cells; missing ones read as "".
        cells = values[offset] if offset < len(values) else []
        rows.append(DisplayedRow(first + offset, *(_text(cells, c - left) for c in columns)))
    return rows


def _text(cells: list, index: int) -> str:
    return str(cells[index]) if index < len(cells) and cells[index] is not None else ""
