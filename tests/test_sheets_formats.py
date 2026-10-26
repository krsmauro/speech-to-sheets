from speech_to_sheets.sheets.formats import FIELDS, formats_for
from speech_to_sheets.sheets.schema import Layout
from tests.fake_sheet import FakeSpreadsheet, FakeWorksheet

DATE_TIME = {"type": "DATE_TIME", "pattern": "dd/mm/yyyy hh:mm"}
MONEY = {"type": "CURRENCY", "pattern": "#,##0.00 [$EUR]"}


def row_formats(cells: list[dict]) -> dict:
    return {"sheets": [{"data": [{"rowData": [{"values": cells}]}]}]}


def test_formats_are_matched_to_columns_that_are_far_apart() -> None:
    # Mapped columns B to F, so the API answers for B, C, D, E, F in that order.
    layout = Layout(date=6, amount=3, category=2, description=5)
    cells = [{}, {"userEnteredFormat": {"numberFormat": MONEY}}, {}, {}]
    cells.append({"userEnteredFormat": {"numberFormat": DATE_TIME, "backgroundColor": {"red": 1}}})
    worksheet = FakeWorksheet([], FakeSpreadsheet(row_formats(cells)))
    assert formats_for(worksheet, layout, 10) == {6: DATE_TIME, 3: MONEY}
    assert worksheet.spreadsheet.requests == [{"ranges": "'Expenses'!B9:F9", "fields": FIELDS}]


def test_only_number_formats_are_asked_for() -> None:
    assert FIELDS == "sheets.data.rowData.values.userEnteredFormat.numberFormat"
