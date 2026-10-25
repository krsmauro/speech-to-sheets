import pytest
from pydantic import ValidationError

from speech_to_sheets.config.columns import Columns


def test_defaults_are_generic_english() -> None:
    columns = Columns()
    assert (columns.date, columns.amount, columns.category, columns.description) == (
        "Date",
        "Amount",
        "Category",
        "Description",
    )


def test_headers_are_stripped() -> None:
    assert Columns(date="  Fecha ").date == "Fecha"


def test_blank_header_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Columns(date="   ")


def test_two_roles_with_the_same_header_are_rejected_ignoring_case() -> None:
    with pytest.raises(ValidationError, match="share one"):
        Columns(date="Total", amount="total")


def test_unknown_role_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Columns(payment_method="Card")
