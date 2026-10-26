from pathlib import Path
from types import SimpleNamespace

import pytest
from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound

from speech_to_sheets.sheets import client
from speech_to_sheets.sheets.client import SCOPES, list_tabs, open_worksheet
from speech_to_sheets.sheets.errors import SheetsError
from tests.fake_sheet import api_error

EMAIL = "bot@project.iam.gserviceaccount.com"


class FakeBook:
    def __init__(self, tabs: list[str]) -> None:
        self.tabs = tabs

    def worksheet(self, title: str) -> SimpleNamespace:
        if title not in self.tabs:
            raise WorksheetNotFound(title)
        return SimpleNamespace(title=title)

    def worksheets(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(title=title) for title in self.tabs]


@pytest.fixture
def google(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Fakes the key file and the API. Set `opens` to a FakeBook or to an error to raise."""
    state: dict = {"opens": FakeBook(["Expenses", "Summary"])}

    def from_file(filename: str, scopes: list[str]) -> SimpleNamespace:
        state.update(filename=filename, scopes=scopes)
        return SimpleNamespace(service_account_email=EMAIL)

    def open_by_key(key: str) -> FakeBook:
        if isinstance(state["opens"], Exception):
            raise state["opens"]
        return state["opens"]

    monkeypatch.setattr(client.Credentials, "from_service_account_file", from_file)
    monkeypatch.setattr(
        client.gspread, "authorize", lambda c: SimpleNamespace(open_by_key=open_by_key)
    )
    return state


def test_opens_the_tab_with_the_sheets_scope_only(google: dict) -> None:
    assert open_worksheet(Path("/keys/k.json"), "sheet-id", "Expenses").title == "Expenses"
    assert google["filename"] == "/keys/k.json"
    assert google["scopes"] == SCOPES == ["https://www.googleapis.com/auth/spreadsheets"]


def test_unknown_or_unshared_sheet_names_the_service_account(google: dict) -> None:
    google["opens"] = SpreadsheetNotFound()
    with pytest.raises(SheetsError, match=f"sheets.sheet_id: .* shared with {EMAIL}"):
        open_worksheet(Path("k.json"), "sheet-id", "Expenses")


def test_refused_access_says_what_to_check_and_why(google: dict) -> None:
    refused = PermissionError()
    refused.__cause__ = api_error(403, "The caller does not have permission")
    google["opens"] = refused
    with pytest.raises(SheetsError) as caught:
        open_worksheet(Path("k.json"), "sheet-id", "Expenses")
    assert EMAIL in str(caught.value) and "Google Sheets API" in str(caught.value)
    assert "The caller does not have permission" in str(caught.value)


def test_unknown_tab_lists_the_tabs(google: dict) -> None:
    with pytest.raises(SheetsError, match="no tab named Spending; tabs found: Expenses, Summary"):
        open_worksheet(Path("k.json"), "sheet-id", "Spending")


@pytest.mark.parametrize("content", ["{}", "not json", '{"type": "authorized_user"}'])
def test_a_file_that_is_not_a_service_account_key_is_rejected(tmp_path: Path, content: str) -> None:
    key = tmp_path / "key.json"
    key.write_text(content)
    with pytest.raises(SheetsError, match="GOOGLE_SERVICE_ACCOUNT_FILE"):
        open_worksheet(key, "sheet-id", "Expenses")


def test_listing_tabs_reports_api_errors() -> None:
    class Broken:
        def worksheets(self) -> list:
            raise api_error(500, "Internal error")

    with pytest.raises(SheetsError, match="listing the tabs: .* 500: Internal error"):
        list_tabs(Broken())
