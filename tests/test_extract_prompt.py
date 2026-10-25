from speech_to_sheets.extract.inputs import ExampleRow
from speech_to_sheets.extract.prompt import build_system_prompt


def test_lists_categories_and_example_rows_in_order() -> None:
    examples = [
        ExampleRow("01/10/2026", "$45,000", "Food", "Market"),
        ExampleRow("02/10/2026", "$12,000", "Transport", "Bus"),
    ]
    prompt = build_system_prompt(["Food", "Transport"], examples)
    assert "- Food\n- Transport" in prompt
    assert prompt.index("01/10/2026 | $45,000 | Food | Market") < prompt.index("Bus")


def test_without_examples_there_is_no_example_section() -> None:
    prompt = build_system_prompt(["Food"], [])
    assert "Recent rows" not in prompt


def test_prompt_is_english_and_names_no_locale() -> None:
    prompt = build_system_prompt(["Food"], [])
    assert prompt.isascii()
    assert "COP" not in prompt and "Spanish" not in prompt
