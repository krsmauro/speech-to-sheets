import re

import pytest
import requests
from google.auth.exceptions import RefreshError

from speech_to_sheets.sheets.errors import SheetsError, WriteError, google_errors
from tests.fake_sheet import api_error


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            api_error(429, "Quota exceeded"),
            "writing row 5: Google Sheets API error 429: Quota exceeded",
        ),
        (RefreshError("invalid_grant: Invalid JWT Signature."), "rejected the service account key"),
        (requests.ConnectionError("down"), "writing row 5: could not reach Google Sheets"),
        (requests.Timeout(), "could not reach Google Sheets"),
    ],
)
def test_library_errors_become_one_readable_error(error: Exception, message: str) -> None:
    with pytest.raises(SheetsError, match=re.escape(message)), google_errors("writing row 5"):
        raise error


def test_other_errors_are_not_hidden() -> None:
    with pytest.raises(KeyError), google_errors("writing row 5"):
        raise KeyError("a bug in our code")


def test_a_write_can_raise_its_own_kind_of_error() -> None:
    with (
        pytest.raises(WriteError, match="writing row 5: could not reach"),
        google_errors("writing row 5", WriteError),
    ):
        raise requests.Timeout()
