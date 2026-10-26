from dataclasses import astuple

import gspread
from gspread.utils import absolute_range_name, rowcol_to_a1

from speech_to_sheets.sheets.errors import google_errors
from speech_to_sheets.sheets.schema import Layout

FIELDS = "sheets.data.rowData.values.userEnteredFormat.numberFormat"
# No pattern: the sheet shows the default date format of its own locale.
DEFAULT_DATE_FORMAT = {"type": "DATE"}


def formats_for(worksheet: gspread.Worksheet, layout: Layout, row: int) -> dict[int, dict]:
    """Number formats for the date and amount cells of a new row, keyed by column.

    Copied from the row above, because a sheet often formats each typed cell, not the whole
    column: a date written as a serial number with no format shows as 46320. Only the number
    format is copied, never colors. The date falls back to the locale's default date format.
    """
    above = _formats_in_row(worksheet, layout, row - 1) if row > 2 else {}
    date_format = above.get(layout.date, {})
    formats = {layout.date: date_format if _is_date(date_format) else DEFAULT_DATE_FORMAT}
    if layout.amount in above:
        formats[layout.amount] = above[layout.amount]
    return formats


def _formats_in_row(worksheet: gspread.Worksheet, layout: Layout, row: int) -> dict[int, dict]:
    columns = astuple(layout)
    left = min(columns)
    span = f"{rowcol_to_a1(row, left)}:{rowcol_to_a1(row, max(columns))}"
    params = {"ranges": absolute_range_name(worksheet.title, span), "fields": FIELDS}
    with google_errors(f"reading the formats of row {row}"):
        metadata = worksheet.spreadsheet.fetch_sheet_metadata(params)
    try:
        cells = metadata["sheets"][0]["data"][0]["rowData"][0]["values"]
    except (KeyError, IndexError):
        return {}
    found = {left + index: cell.get("userEnteredFormat", {}) for index, cell in enumerate(cells)}
    return {column: f["numberFormat"] for column, f in found.items() if "numberFormat" in f}


def _is_date(number_format: dict) -> bool:
    return number_format.get("type") in ("DATE", "DATE_TIME")
