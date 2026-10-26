from datetime import date
from decimal import Decimal

import pytest

from speech_to_sheets.extract.sanity import check
from speech_to_sheets.extract.schema import Complete, NeedsInfo

CATEGORIES = ["Food", "Transport"]
TODAY = date(2026, 10, 25)


def entry(amount: str = "20", category: str = "Food", day: date = TODAY) -> Complete:
    return Complete(Decimal(amount), category, "Market", day)


@pytest.mark.parametrize("amount", ["20000", "0.5", "12.49"])
def test_good_entry_passes_through_whatever_the_size(amount: str) -> None:
    good = entry(amount)
    assert check(good, CATEGORIES, TODAY) is good


def test_questions_pass_through() -> None:
    question = NeedsInfo("How much?")
    assert check(question, CATEGORIES, TODAY) is question


def test_unknown_category_asks_and_lists_the_options() -> None:
    result = check(entry(category="Cars"), CATEGORIES, TODAY)
    assert isinstance(result, NeedsInfo)
    assert "Food, Transport" in result.question


@pytest.mark.parametrize("amount", ["0", "-5", "-0.01"])
def test_amount_must_be_positive(amount: str) -> None:
    assert isinstance(check(entry(amount), CATEGORIES, TODAY), NeedsInfo)


@pytest.mark.parametrize("day", [TODAY, date(2026, 10, 24), date(2025, 1, 1)])
def test_today_and_past_dates_pass(day: date) -> None:
    good = entry(day=day)
    assert check(good, CATEGORIES, TODAY) is good


def test_a_date_after_today_asks_and_shows_the_date_read() -> None:
    result = check(entry(day=date(2026, 10, 26)), CATEGORIES, TODAY)
    assert isinstance(result, NeedsInfo)
    assert "2026-10-26" in result.question
