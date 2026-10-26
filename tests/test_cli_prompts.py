import pytest

from tests.scripted import Script


def test_ask_strips_the_answer_and_shows_the_default() -> None:
    script = Script("  Lisbon  ")
    assert script.prompter.ask("City", default="Paris") == "Lisbon"
    assert script.questions == ["City [Paris]: "]


def test_ask_blank_takes_the_default() -> None:
    assert Script("").prompter.ask("City", default="Paris") == "Paris"
    assert Script(" ").prompter.ask("Note") == ""


def test_ask_repeats_until_the_check_passes() -> None:
    script = Script("", "x", "ok")

    def check(answer: str) -> str | None:
        return None if answer == "ok" else f"not {answer!r}"

    assert script.prompter.ask("Word", check=check) == "ok"
    assert script.said == ["not ''", "not 'x'"]
    assert len(script.questions) == 3


@pytest.mark.parametrize(
    ("answer", "default", "expected"),
    [
        ("", True, True),
        ("", False, False),
        ("Y", False, True),
        ("yes", False, True),
        ("n", True, False),
        ("NO", True, False),
    ],
)
def test_confirm(answer: str, default: bool, expected: bool) -> None:
    assert Script(answer).prompter.confirm("Go on?", default) is expected


def test_confirm_shows_the_default_and_repeats_on_other_answers() -> None:
    script = Script("maybe", "y")
    assert script.prompter.confirm("Replace it?", False) is True
    assert script.questions == ["Replace it? [y/N]: "] * 2
    assert script.said == ["Answer y or n."]


def test_choose_lists_the_options_and_returns_the_index() -> None:
    script = Script("2")
    assert script.prompter.choose("Which tab?", ["Summary", "Expenses"]) == 1
    assert script.said == ["  1. Summary", "  2. Expenses"]
    assert script.questions == ["Which tab?: "]


def test_choose_blank_takes_the_default() -> None:
    script = Script("")
    assert script.prompter.choose("Which?", ["a", "b", "c"], default=2) == 2
    assert script.questions == ["Which? [3]: "]


def test_choose_repeats_on_a_number_out_of_range_or_not_a_number() -> None:
    script = Script("0", "3", "two", "", "1")
    assert script.prompter.choose("Which?", ["a", "b"]) == 0
    assert script.said[2:] == ["Type a number from 1 to 2."] * 4
