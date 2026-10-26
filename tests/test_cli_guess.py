from speech_to_sheets.cli.guess import guess_columns
from speech_to_sheets.sheets.sample import ColumnSample as Sample


def test_guesses_every_role_from_the_cells_whatever_the_header_language() -> None:
    samples = [
        Sample(1, "Details", texts=["Market", "Bakery", "Fuel"]),
        Sample(2, "Kind", dropdowns=3, texts=["Food", "Food", "Car"]),
        Sample(3, "Paid", numbers=3),
        Sample(4, "When", dates=3),
    ]
    assert guess_columns(samples) == {"date": 4, "amount": 3, "category": 2, "description": 1}


def test_the_english_default_names_win_over_the_content() -> None:
    samples = [
        Sample(1, "Total", numbers=5),
        Sample(2, "amount", texts=["about 20"]),
        Sample(3, "DATE", texts=["yesterday"]),
    ]
    assert guess_columns(samples) == {"amount": 2, "date": 3}


def test_on_a_tie_the_leftmost_column_wins() -> None:
    samples = [Sample(1, "Spent", numbers=2), Sample(2, "Balance", numbers=2)]
    assert guess_columns(samples) == {"amount": 1}


def test_a_second_dropdown_column_is_never_the_description() -> None:
    samples = [
        Sample(1, "Kind", dropdowns=3, texts=["Food", "Food", "Car"]),
        Sample(2, "Paid with", dropdowns=3, texts=["Cash", "Card", "Bank"]),
        Sample(3, "Note", texts=["Market"]),
    ]
    assert guess_columns(samples) == {"category": 1, "description": 3}


def test_without_a_dropdown_the_category_is_left_to_the_user() -> None:
    samples = [
        Sample(1, "Kind", texts=["Food", "Food", "Car"]),
        Sample(2, "Details", texts=["Market", "Bakery", "Fuel"]),
    ]
    assert guess_columns(samples) == {"description": 2}


def test_each_column_gets_one_role_at_most() -> None:
    samples = [Sample(1, "When", dates=3, numbers=1, dropdowns=1, texts=["x"])]
    assert guess_columns(samples) == {"date": 1}


def test_empty_or_unnamed_columns_are_never_guessed() -> None:
    samples = [Sample(1, "", dates=4, numbers=4), Sample(2, "Notes"), Sample(3, "Other")]
    assert guess_columns(samples) == {}
