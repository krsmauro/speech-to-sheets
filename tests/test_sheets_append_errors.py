from datetime import date
from decimal import Decimal

import pytest
import requests

from speech_to_sheets.sheets.append import append_entry
from speech_to_sheets.sheets.errors import SheetsError, WriteError
from speech_to_sheets.sheets.schema import Layout
from tests.fake_sheet import FakeWorksheet

ENTRY = {"day": date(2025, 1, 14), "amount": Decimal(5), "category": "Food", "description": "x"}


def raise_timeout(*args: object) -> None:
    raise requests.Timeout()


def test_a_failed_write_request_is_a_write_error() -> None:
    worksheet = FakeWorksheet([["Date", "Amount", "Category", "Description"]])
    worksheet.spreadsheet.batch_update = raise_timeout
    with pytest.raises(WriteError, match="writing row 2: could not reach Google Sheets"):
        append_entry(worksheet, Layout(1, 2, 3, 4), **ENTRY)


def test_a_failed_read_before_the_write_is_not_a_write_error() -> None:
    worksheet = FakeWorksheet([["Date", "Amount", "Category", "Description"]])
    worksheet.col_values = raise_timeout
    with pytest.raises(SheetsError) as caught:
        append_entry(worksheet, Layout(1, 2, 3, 4), **ENTRY)
    assert not isinstance(caught.value, WriteError), "nothing was sent, so nothing to check"
