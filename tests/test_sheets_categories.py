import pytest

from speech_to_sheets.sheets.categories import FIELDS, read_categories
from speech_to_sheets.sheets.errors import SheetsError
from tests.fake_sheet import FakeSpreadsheet, FakeWorksheet


def validation(condition: dict) -> dict:
    """The shape the Sheets API returns for one cell's data validation rule."""
    rule = {"condition": condition, "showCustomUi": True}
    return {"sheets": [{"data": [{"rowData": [{"values": [{"dataValidation": rule}]}]}]}]}


def one_of_list(*values: str) -> dict:
    return validation({"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in values]})


def sheet(metadata: dict, ranges: dict | None = None) -> FakeWorksheet:
    return FakeWorksheet([], FakeSpreadsheet(metadata, ranges))


def test_reads_the_dropdown_of_the_first_data_row() -> None:
    worksheet = sheet(one_of_list("Food", " Café ", "", "Food", "Transport"))
    assert read_categories(worksheet, 3, ["Unused"]) == ["Food", "Café", "Transport"]
    assert worksheet.spreadsheet.requests == [{"ranges": "'Expenses'!C2", "fields": FIELDS}]


@pytest.mark.parametrize(
    ("formula", "range_name"),
    [
        ("=Lists!$A$2:$A$4", "Lists!A2:A4"),
        ("='My lists'!A2:A4", "'My lists'!A2:A4"),
        ("=$H$2:$H$4", "'Expenses'!H2:H4"),
    ],
)
def test_reads_a_dropdown_fed_by_a_range(formula: str, range_name: str) -> None:
    metadata = validation({"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": formula}]})
    worksheet = sheet(metadata, {range_name: [["Food"], ["Transport"], [""]]})
    assert read_categories(worksheet, 3, []) == ["Food", "Transport"]


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"sheets": [{"data": [{}]}]},
        validation({"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0"}]}),
        one_of_list(" "),
    ],
)
def test_without_a_readable_dropdown_the_fallback_is_used(metadata: dict) -> None:
    assert read_categories(sheet(metadata), 3, ["Food"]) == ["Food"]


def test_no_dropdown_and_no_fallback_says_what_to_do() -> None:
    with pytest.raises(SheetsError, match="fallback_categories is empty"):
        read_categories(sheet({}), 3, [])
