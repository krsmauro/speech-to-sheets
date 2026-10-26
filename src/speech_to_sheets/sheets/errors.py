from collections.abc import Iterator
from contextlib import contextmanager

import requests
from google.auth.exceptions import GoogleAuthError
from gspread.exceptions import APIError


class SheetsError(Exception):
    """A Google Sheets step failed. The message is safe to show to the user."""


class WriteError(SheetsError):
    """The write request itself failed. Google may have stored the row anyway (for example
    when only its answer timed out), so the user must check the sheet before resending."""


@contextmanager
def google_errors(action: str, kind: type[SheetsError] = SheetsError) -> Iterator[None]:
    """Turn library errors into one SheetsError (or `kind`) that says what was being done."""
    try:
        yield
    except APIError as error:
        message = error.error.get("message", "no details")
        raise kind(f"{action}: Google Sheets API error {error.code}: {message}") from None
    except GoogleAuthError as error:
        raise kind(f"{action}: Google rejected the service account key ({error})") from None
    except requests.RequestException:
        raise kind(f"{action}: could not reach Google Sheets (network or timeout)") from None
