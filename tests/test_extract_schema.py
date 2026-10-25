import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from speech_to_sheets.extract.schema import (
    FALLBACK_QUESTION,
    Complete,
    NeedsInfo,
    build_output_model,
    to_result,
)
from tests.fake_anthropic import answer

# An accented category checks that non-ASCII values survive the schema round trip.
MODEL = build_output_model(["Food", "Café"])


def parse(**fields: object) -> Complete | NeedsInfo:
    return to_result(MODEL.model_validate(answer(**fields)))


def test_schema_is_strict_and_lists_the_categories() -> None:
    schema = MODEL.model_json_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["properties"]["category"]["anyOf"][0]["enum"] == ["Food", "Café"]


def test_amount_is_a_plain_number_in_the_schema() -> None:
    amount = MODEL.model_json_schema()["properties"]["amount"]
    assert amount["anyOf"] == [{"type": "number"}, {"type": "null"}]


@pytest.mark.parametrize("raw", ["15.49", "0.1", "1234567.89", "20000"])
def test_amounts_are_parsed_exactly_from_the_json_text(raw: str) -> None:
    text = json.dumps(answer(status="complete", category="Food", description="x"))
    output = MODEL.model_validate_json(text.replace('"amount": null', f'"amount": {raw}'))
    assert output.amount == Decimal(raw)


def test_unknown_category_fails_validation() -> None:
    data = answer(status="complete", amount=1, category="Cars")
    with pytest.raises(ValidationError):
        MODEL.model_validate(data)


def test_no_categories_is_an_error() -> None:
    with pytest.raises(ValueError):
        build_output_model([])


def test_complete_answer() -> None:
    result = parse(status="complete", amount=4.5, category="Café", description=" Latte ")
    assert result == Complete(Decimal("4.5"), "Café", "Latte")


@pytest.mark.parametrize(
    "fields",
    [
        {"amount": None, "category": "Food", "description": "Market"},
        {"amount": 10, "category": None, "description": "Market"},
        {"amount": 10, "category": "Food", "description": "  "},
    ],
)
def test_complete_with_a_missing_field_becomes_a_question(fields: dict) -> None:
    assert parse(status="complete", question="What was it?", **fields) == NeedsInfo("What was it?")


def test_needs_info_without_a_question_uses_the_fallback() -> None:
    assert parse(status="needs_info", question=" ") == NeedsInfo(FALLBACK_QUESTION)
