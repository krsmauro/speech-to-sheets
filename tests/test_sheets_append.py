from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

import pytest

from speech_to_sheets.sheets.append import append_entry
from speech_to_sheets.sheets.formats import DEFAULT_DATE_FORMAT
from speech_to_sheets.sheets.schema import Layout
from tests.fake_sheet import FakeSpreadsheet, FakeWorksheet

HEADER = ["Date", "Amount", "Category", "Description", "", "Notes"]
ROWS = [HEADER, ["x", "1", "Food", "A", "", "note"], ["y", "2", "Food", "B"]]
LAYOUT = Layout(1, 2, 3, 4)
DAY = date(2000, 1, 1)  # serial number 36526
DATE_FORMAT = {"type": "DATE", "pattern": "d/m/yyyy"}
MONEY = {"type": "CURRENCY", "pattern": '"$"#,##0'}


def formats_above(*formats: dict | None) -> dict:
    """Metadata shaped like the API's answer for the number formats of one row."""
    cells = [{"userEnteredFormat": {"numberFormat": f}} if f else {} for f in formats]
    return {"sheets": [{"data": [{"rowData": [{"values": cells}]}]}]}


def append(worksheet: FakeWorksheet, **changes: object) -> int:
    entry = {"day": DAY, "amount": Decimal("12.50"), "category": "Food", "description": "Market"}
    return append_entry(worksheet, LAYOUT, **(entry | changes))


def cells_written(worksheet: FakeWorksheet) -> dict[tuple[int, int], dict]:
    [body] = worksheet.spreadsheet.updates
    found = {}
    for request in body["requests"]:
        update = request["updateCells"]
        start = update["start"]
        assert start["sheetId"] == worksheet.id
        cell = update["rows"][0]["values"][0]
        found[(start["rowIndex"], start["columnIndex"])] = {**cell, "fields": update["fields"]}
    return found


def test_writes_only_the_four_cells_of_the_next_row_in_one_request() -> None:
    worksheet = FakeWorksheet(ROWS, FakeSpreadsheet(formats_above(DATE_FORMAT, MONEY)))
    worksheet.cells[(223, 6)] = "unrelated content further down another column"
    assert append(worksheet, description="=IMPORTXML(a, b)") == 4
    assert cells_written(worksheet) == {
        (3, 0): {
            "userEnteredValue": {"numberValue": 36526},
            "userEnteredFormat": {"numberFormat": DATE_FORMAT},
            "fields": "userEnteredValue,userEnteredFormat.numberFormat",
        },
        (3, 1): {
            "userEnteredValue": {"numberValue": 12.5},
            "userEnteredFormat": {"numberFormat": MONEY},
            "fields": "userEnteredValue,userEnteredFormat.numberFormat",
        },
        (3, 2): {"userEnteredValue": {"stringValue": "Food"}, "fields": "userEnteredValue"},
        # A string value is stored as text; formulas would need formulaValue.
        (3, 3): {
            "userEnteredValue": {"stringValue": "=IMPORTXML(a, b)"},
            "fields": "userEnteredValue",
        },
    }
    assert worksheet.spreadsheet.requests[0]["ranges"] == "'Expenses'!A3:D3"


@pytest.mark.parametrize("above", [formats_above(), formats_above({"type": "TEXT"}), {}])
def test_without_a_date_format_above_the_default_date_format_is_used(above: dict) -> None:
    worksheet = FakeWorksheet(ROWS, FakeSpreadsheet(above))
    append(worksheet)
    written = cells_written(worksheet)
    assert written[(3, 0)]["userEnteredFormat"] == {"numberFormat": DEFAULT_DATE_FORMAT}
    assert written[(3, 1)]["fields"] == "userEnteredValue", "no amount format is invented"


def test_first_entry_goes_under_the_header_with_the_default_date_format() -> None:
    worksheet = FakeWorksheet([HEADER])
    assert append(worksheet) == 2
    assert worksheet.spreadsheet.requests == [], "the header row is not copied"
    assert cells_written(worksheet)[(1, 0)]["userEnteredFormat"]["numberFormat"] == {"type": "DATE"}


@pytest.mark.parametrize(
    ("amount", "sent"), [("20000", 20000), ("1250.00", 1250), ("15.49", 15.49), ("0.1", 0.1)]
)
def test_amounts_are_sent_as_plain_numbers(amount: str, sent: float) -> None:
    worksheet = FakeWorksheet([HEADER])
    append(worksheet, amount=Decimal(amount))
    value = worksheet.cells[(2, 2)]
    assert value == sent
    assert type(value) is type(sent)


def test_entries_written_at_the_same_time_get_different_rows() -> None:
    worksheet = FakeWorksheet([HEADER], delay=0.02)
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda i: append(worksheet, description=f"entry {i}"), range(4)))
    assert sorted(rows) == [2, 3, 4, 5]
