from collections.abc import Iterator
from contextlib import contextmanager

import requests
from google.auth.exceptions import GoogleAuthError
from gspread.exceptions import APIError


class SheetsError(Exception):
    """A Google Sheets step failed. The message is safe to show to the user."""


@contextmanager
def google_errors(action: str) -> Iterator[None]:
    """Turn library errors into one SheetsError that says what was being done."""
    try:
        yield
    except APIError as error:
        message = error.error.get("message", "no details")
        raise SheetsError(f"{action}: Google Sheets API error {error.code}: {message}") from None
    except GoogleAuthError as error:
        raise SheetsError(f"{action}: Google rejected the service account key ({error})") from None
    except requests.RequestException:
        raise SheetsError(f"{action}: could not reach Google Sheets (network or timeout)") from None
