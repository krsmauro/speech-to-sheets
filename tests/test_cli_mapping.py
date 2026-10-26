import pytest

from speech_to_sheets.cli.mapping import confirm_columns
from speech_to_sheets.config.columns import Columns
from speech_to_sheets.sheets.errors import SheetsError
from speech_to_sheets.sheets.sample import ColumnSample as Sample
from speech_to_sheets.sheets.schema import Layout
from tests.scripted import Script

CLEAR = [
    Sample(1, "When", dates=2),
    Sample(2, "Paid", numbers=2),
    Sample(3, "Kind", dropdowns=2),
    Sample(4, "Notes", texts=["a", "b", "c"]),
    Sample(5, "Details", texts=["x", "y"]),
]


def test_accepting_the_proposal() -> None:
    script = Script("")
    columns, layout = confirm_columns(script.prompter, CLEAR)
    assert columns == Columns(date="When", amount="Paid", category="Kind", description="Notes")
    assert layout == Layout(date=1, amount=2, category=3, description=4)
    assert "Headers in row 1: A When, B Paid, C Kind, D Notes, E Details" in script.output
    assert "  description: D Notes" in script.output


def test_declining_lets_the_user_pick_each_role_with_the_guess_as_default() -> None:
    script = Script("n", "", "", "", "2")
    columns, layout = confirm_columns(script.prompter, CLEAR)
    assert columns.description == "Details" and layout.description == 5
    assert script.questions[-1] == "Which column holds the description? [1]: "
    assert script.said[-2:] == ["  1. D Notes", "  2. E Details"]  # picked columns are gone


def test_an_incomplete_guess_goes_straight_to_picking() -> None:
    samples = [Sample(1, "When", dates=1), Sample(2, "Paid"), Sample(3, "Kind"), Sample(4, "X")]
    script = Script("", "1", "1", "1")
    columns, _ = confirm_columns(script.prompter, samples)
    assert columns == Columns(date="When", amount="Paid", category="Kind", description="X")
    assert "Could not guess every column. Pick them below." in script.output
    assert script.questions[1] == "Which column holds the amount?: "  # no guess, no default


def test_fewer_than_four_headers_is_an_error() -> None:
    samples = [Sample(1, "When"), Sample(2, ""), Sample(3, "Paid"), Sample(4, "Kind")]
    with pytest.raises(
        SheetsError, match="row 1 needs a header for each .* A When, C Paid, D Kind"
    ):
        confirm_columns(Script().prompter, samples)


def test_a_header_used_in_two_columns_cannot_be_mapped() -> None:
    samples = [*CLEAR[:4], Sample(5, "when")]
    with pytest.raises(SheetsError, match="'When' is in more than one column.*rename"):
        confirm_columns(Script("").prompter, samples)
