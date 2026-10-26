from datetime import timedelta

from speech_to_sheets.sheets.dates import SERIAL_EPOCH
from tests.fake_sheet import FakeSpreadsheet, FakeWorksheet

CATEGORIES = ["Food", "Transport", "Pets"]
DATE_FORMAT = {"type": "DATE", "pattern": "d/m/yyyy"}
MONEY = {"type": "CURRENCY", "pattern": '"$"#,##0.00'}
HEADER = ["Date", "Amount", "Category", "Description"]
# Dates as serial numbers and amounts as numbers, as the sheet stores them.
ROWS = [HEADER, [45000, 45.2, "Food", "Bakery"], [45001, 12, "Transport", "Bus"]]

_DROPDOWN = {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": c} for c in CATEGORIES]}


def _one_row(*cells: dict) -> dict:
    """Metadata shaped like the API's answer for one row of cells."""
    return {"sheets": [{"data": [{"rowData": [{"values": list(cells)}]}]}]}


# The fake answers every metadata request alike, so one row of cells serves both reads:
# the dropdown of the first data row and the number formats of the row above a new entry.
METADATA = _one_row(
    {
        "dataValidation": {"condition": _DROPDOWN},
        "userEnteredFormat": {"numberFormat": DATE_FORMAT},
    },
    {"userEnteredFormat": {"numberFormat": MONEY}},
)


class ShownWorksheet(FakeWorksheet):
    """A fake sheet whose reads come back formatted, like the API's FORMATTED_VALUE: the
    first column as d/m/yyyy dates, the second as dollar amounts."""

    def __init__(self) -> None:
        super().__init__(ROWS, FakeSpreadsheet(METADATA))

    def get(self, range_name: str, value_render_option: str | None = None) -> list[list]:
        rows = super().get(range_name, value_render_option)
        return [[_shown(index, cell) for index, cell in enumerate(row)] for row in rows]


def _shown(index: int, cell: object) -> object:
    if index == 0 and isinstance(cell, int):
        day = SERIAL_EPOCH + timedelta(days=cell)
        return f"{day.day}/{day.month}/{day.year}"
    if index == 1 and isinstance(cell, int | float):
        return f"${cell:,.2f}"
    return cell
