from decimal import Decimal

import pytest

from speech_to_sheets.extract.sanity import check
from speech_to_sheets.extract.schema import Complete, NeedsInfo

CATEGORIES = ["Food", "Transport"]


@pytest.mark.parametrize("amount", ["20000", "0.5", "12.49"])
def test_good_entry_passes_through_whatever_the_size(amount: str) -> None:
    entry = Complete(Decimal(amount), "Food", "Market")
    assert check(entry, CATEGORIES) is entry


def test_questions_pass_through() -> None:
    question = NeedsInfo("How much?")
    assert check(question, CATEGORIES) is question


def test_unknown_category_asks_and_lists_the_options() -> None:
    result = check(Complete(Decimal(20), "Cars", "Fuel"), CATEGORIES)
    assert isinstance(result, NeedsInfo)
    assert "Food, Transport" in result.question


@pytest.mark.parametrize("amount", ["0", "-5", "-0.01"])
def test_amount_must_be_positive(amount: str) -> None:
    result = check(Complete(Decimal(amount), "Food", "Market"), CATEGORIES)
    assert isinstance(result, NeedsInfo)
