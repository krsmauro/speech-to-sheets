import threading
from datetime import date
from decimal import Decimal

import gspread

from speech_to_sheets.sheets.dates import to_serial
from speech_to_sheets.sheets.errors import WriteError, google_errors
from speech_to_sheets.sheets.formats import formats_for
from speech_to_sheets.sheets.rows import last_filled_row
from speech_to_sheets.sheets.schema import Layout

# Slack runs handlers on several threads; two entries must never pick the same empty row.
# This guards one process only: never run two copies of the bot against one sheet.
_one_writer = threading.Lock()


def append_entry(
    worksheet: gspread.Worksheet,
    layout: Layout,
    *,
    day: date,
    amount: Decimal,
    category: str,
    description: str,
) -> int:
    """Write one entry in the row after the last date, touching only the four mapped cells.

    One request, so Google applies all of it or none. Values are literal: numbers stay numbers
    and text is never run as a formula. Returns the row number. A failed write request
    raises WriteError (the row may exist anyway); a failed read before it, SheetsError.
    """
    values = {
        layout.date: {"numberValue": to_serial(day)},
        layout.amount: {"numberValue": _number(amount)},
        layout.category: {"stringValue": category},
        layout.description: {"stringValue": description},
    }
    with _one_writer:
        row = last_filled_row(worksheet, layout) + 1
        formats = formats_for(worksheet, layout, row)
        requests = [
            _update_cell(worksheet.id, row, column, value, formats.get(column))
            for column, value in values.items()
        ]
        with google_errors(f"writing row {row}", WriteError):
            worksheet.spreadsheet.batch_update({"requests": requests})
    return row


def _update_cell(
    sheet_id: int, row: int, column: int, value: dict, number_format: dict | None
) -> dict:
    cell: dict = {"userEnteredValue": value}
    fields = "userEnteredValue"
    if number_format:
        cell["userEnteredFormat"] = {"numberFormat": number_format}
        fields += ",userEnteredFormat.numberFormat"  # the mask leaves every other format alone
    start = {"sheetId": sheet_id, "rowIndex": row - 1, "columnIndex": column - 1}
    return {"updateCells": {"rows": [{"values": [cell]}], "fields": fields, "start": start}}


def _number(amount: Decimal) -> int | float:
    """JSON has no decimal type: whole amounts go as integers, others as the closest float."""
    return int(amount) if amount == amount.to_integral_value() else float(amount)
