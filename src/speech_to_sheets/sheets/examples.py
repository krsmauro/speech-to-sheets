import gspread

from speech_to_sheets.sheets.rows import DisplayedRow, last_filled_row, read_rows
from speech_to_sheets.sheets.schema import Layout


def read_examples(worksheet: gspread.Worksheet, layout: Layout, count: int) -> list[DisplayedRow]:
    """The last `count` entries, oldest first, shown to Claude as naming examples."""
    if count < 1:
        return []
    last = last_filled_row(worksheet, layout)
    if last < 2:
        return []
    rows = read_rows(worksheet, layout, max(2, last - count + 1), last)
    return [r for r in rows if r.date or r.amount or r.category or r.description]
