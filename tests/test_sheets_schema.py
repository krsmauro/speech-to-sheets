import pytest

from speech_to_sheets.config.columns import Columns
from speech_to_sheets.sheets.errors import SheetsError
from speech_to_sheets.sheets.schema import Layout, find_layout, read_layout
from tests.fake_sheet import FakeWorksheet

COLUMNS = Columns()  # Date, Amount, Category, Description


def test_finds_columns_in_any_order_ignoring_case_and_spaces() -> None:
    headers = ["Notes", " description ", "AMOUNT", None, "Date", "category"]
    assert find_layout(headers, COLUMNS) == Layout(date=5, amount=3, category=6, description=2)


def test_uses_the_header_names_from_config() -> None:
    columns = Columns(date="Day", amount="Total", category="Type", description="What")
    assert find_layout(["What", "Type", "Total", "Day"], columns) == Layout(4, 3, 2, 1)


def test_lists_every_missing_header_and_the_headers_found() -> None:
    with pytest.raises(SheetsError) as caught:
        find_layout(["Date", "Price", "Category"], COLUMNS)
    message = str(caught.value)
    assert "sheets.columns.amount: no header 'Amount' in row 1" in message
    assert "sheets.columns.description: no header 'Description'" in message
    assert "Headers found in row 1: Date, Price, Category" in message


def test_a_header_in_two_columns_is_an_error() -> None:
    with pytest.raises(SheetsError, match="header 'Date' is in columns A, E"):
        find_layout(["Date", "Amount", "Category", "Description", "date"], COLUMNS)


def test_empty_header_row() -> None:
    with pytest.raises(SheetsError, match="Headers found in row 1: none"):
        find_layout([], COLUMNS)


def test_read_layout_reads_row_one() -> None:
    sheet = FakeWorksheet([["Date", "Amount", "Category", "Description"], ["x", "y"]])
    assert read_layout(sheet, COLUMNS) == Layout(1, 2, 3, 4)
