from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, WithJsonSchema, create_model

FALLBACK_QUESTION = "How much did you spend, and on what?"

# Parsed straight from the JSON text, so 15.49 stays exactly 15.49 (no float rounding).
# The schema says plain number; Pydantic's default for Decimal would also allow a string.
Amount = Annotated[Decimal, WithJsonSchema({"type": "number"})]


@dataclass(frozen=True)
class Complete:
    amount: Decimal
    category: str
    description: str


@dataclass(frozen=True)
class NeedsInfo:
    question: str


Result = Complete | NeedsInfo


class _Strict(BaseModel):
    # extra="forbid" puts additionalProperties: false in the schema, which the API requires.
    model_config = ConfigDict(extra="forbid")


def build_output_model(categories: list[str]) -> type[BaseModel]:
    """The JSON shape Claude must return. The category enum comes from the sheet at runtime."""
    if not categories:
        raise ValueError("at least one category is needed")
    return create_model(
        "Extraction",
        __base__=_Strict,
        status=(Literal["complete", "needs_info"], ...),
        amount=(Amount | None, ...),
        category=(Literal[tuple(categories)] | None, ...),
        description=(str | None, ...),
        question=(str | None, ...),
    )


def to_result(output: BaseModel) -> Result:
    """Complete only when Claude says so and every field is filled; otherwise a question."""
    description = (output.description or "").strip()
    if (
        output.status == "complete"
        and output.amount is not None
        and output.category
        and description
    ):
        return Complete(output.amount, output.category, description)
    return NeedsInfo((output.question or "").strip() or FALLBACK_QUESTION)
