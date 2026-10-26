import gspread

from speech_to_sheets.sheets.rows import DisplayedRow, read_rows
from speech_to_sheets.sheets.schema import Layout


def read_row(worksheet: gspread.Worksheet, layout: Layout, row: int) -> DisplayedRow:
    """Read a row back after writing it, so the confirmation shows what is really stored."""
    return read_rows(worksheet, layout, row, row)[0]
