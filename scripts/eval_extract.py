"""Run extraction against the real Claude API over a cases file and print the results.

Costs real money: about a cent or less per run of ~20 cases with Haiku 5.5.
Needs ANTHROPIC_API_KEY in the environment or in .env; no other secret is required.

    uv run python scripts/eval_extract.py [evals/extract_cases.yaml]
"""

import os
import sys
import time
from decimal import Decimal
from pathlib import Path

import yaml
from dotenv import dotenv_values

from speech_to_sheets.extract.client import extract, make_client
from speech_to_sheets.extract.errors import ExtractError
from speech_to_sheets.extract.inputs import ExampleRow, ExtractionInput, Turn
from speech_to_sheets.extract.schema import Complete, NeedsInfo

DEFAULT_CASES = Path("evals/extract_cases.yaml")


class UsageRecorder:
    """Wraps the client to add up token usage across calls."""

    def __init__(self, client: object) -> None:
        self._client = client
        self.messages = self
        self.input_tokens = 0
        self.output_tokens = 0

    def create(self, **kwargs: object) -> object:
        response = self._client.messages.create(**kwargs)
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens
        return response


def to_input(case: dict) -> ExtractionInput:
    thread = case.get("thread") or [{"author": "user", **case}]
    turns = tuple(Turn(t["author"], t["text"], t.get("voice", False)) for t in thread)
    return ExtractionInput(turns=turns)


def passes(result: object, expect: str | dict) -> bool:
    if expect == "needs_info":
        return isinstance(result, NeedsInfo)
    if not isinstance(result, Complete):
        return False
    # YAML reads 15.49 as a float; go through str so it compares exactly with the Decimal.
    wanted_amount = Decimal(str(expect.get("amount", result.amount)))
    wanted_category = expect.get("category", result.category)
    wanted_description = expect.get("description", "").casefold()
    return (
        result.amount == wanted_amount
        and result.category == wanted_category
        and wanted_description in result.description.casefold()
    )


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CASES
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    key = os.environ.get("ANTHROPIC_API_KEY") or dotenv_values(".env").get("ANTHROPIC_API_KEY")
    if not key:
        print("ANTHROPIC_API_KEY is not set (environment or .env)")
        return 2
    client = UsageRecorder(make_client(key))
    examples = [ExampleRow(*map(str, row)) for row in data.get("examples", [])]
    passed = 0
    previous_error = None
    for case in data["cases"]:
        start = time.monotonic()
        try:
            result = extract(client, to_input(case), data["categories"], examples, data["model"])
        except ExtractError as error:
            result = f"ERROR: {error}"
            if result == previous_error:
                print(f"Stopping: the same error twice in a row.\n{result}")
                return 1
            previous_error = result
        ok = passes(result, case["expect"])
        passed += ok
        print(
            f"{'PASS' if ok else 'FAIL'} {time.monotonic() - start:4.1f}s  {case['name']}: {result}"
        )
    total = len(data["cases"])
    print(f"\n{passed}/{total} passed; tokens in {client.input_tokens}, out {client.output_tokens}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
