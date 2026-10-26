from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

from speech_to_sheets.sheets.errors import SheetsError, google_errors

# Only the Sheets scope: the bot never needs the rest of the Google Drive.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def open_worksheet(key_file: Path, sheet_id: str, tab: str) -> gspread.Worksheet:
    """Open the configured tab with the service account. Done once, at startup."""
    spreadsheet = open_spreadsheet(key_file, sheet_id)
    with google_errors("opening the tab"):
        try:
            return spreadsheet.worksheet(tab)
        except WorksheetNotFound:
            tabs = ", ".join(sheet.title for sheet in list_tabs(spreadsheet))
            raise SheetsError(f"sheets.tab: no tab named {tab}; tabs found: {tabs}") from None


def open_spreadsheet(key_file: Path, sheet_id: str) -> gspread.Spreadsheet:
    """Open the whole spreadsheet. Errors name the service account to share it with."""
    try:
        credentials = Credentials.from_service_account_file(str(key_file), scopes=SCOPES)
    except (ValueError, OSError) as error:
        raise SheetsError(
            f"GOOGLE_SERVICE_ACCOUNT_FILE is not a usable service account key: {error}"
        ) from None
    email = credentials.service_account_email
    with google_errors("opening the spreadsheet"):
        try:
            return gspread.authorize(credentials).open_by_key(sheet_id)
        except SpreadsheetNotFound:
            raise SheetsError(
                f"sheets.sheet_id: no spreadsheet with this ID is shared with {email}"
            ) from None
        except PermissionError as error:
            raise SheetsError(
                f"Google refused access. Share the sheet with {email} as Editor, and check that"
                f" the Google Sheets API is enabled in the key's project ({_reason(error)})"
            ) from None


def list_tabs(spreadsheet: gspread.Spreadsheet) -> list[gspread.Worksheet]:
    with google_errors("listing the tabs"):
        return spreadsheet.worksheets()


def _reason(error: PermissionError) -> str:
    """gspread hides the API's 403 behind PermissionError; its own sentence is the cause."""
    cause = error.__cause__
    return cause.error.get("message", "no details") if isinstance(cause, APIError) else "no details"
