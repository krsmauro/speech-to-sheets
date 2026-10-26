from speech_to_sheets.sheets.examples import read_examples
from speech_to_sheets.sheets.read_row import read_row
from speech_to_sheets.sheets.rows import DisplayedRow
from speech_to_sheets.sheets.schema import Layout
from tests.fake_sheet import FakeWorksheet

HEADER = ["Date", "Amount", "Category", "Description"]
LAYOUT = Layout(1, 2, 3, 4)


def sheet_with(entries: int) -> FakeWorksheet:
    rows = [[f"0{i}/10/2026", f"${i}.00", "Food", f"Shop {i}"] for i in range(1, entries + 1)]
    return FakeWorksheet([HEADER, *rows])


def test_examples_are_the_last_rows_oldest_first() -> None:
    rows = read_examples(sheet_with(5), LAYOUT, 3)
    assert [row.description for row in rows] == ["Shop 3", "Shop 4", "Shop 5"]
    assert rows[0] == DisplayedRow(4, "03/10/2026", "$3.00", "Food", "Shop 3")


def test_fewer_entries_than_asked_returns_them_all() -> None:
    assert len(read_examples(sheet_with(2), LAYOUT, 30)) == 2


def test_no_entries_or_no_examples_wanted_returns_nothing() -> None:
    assert read_examples(FakeWorksheet([HEADER]), LAYOUT, 30) == []
    assert read_examples(FakeWorksheet([]), LAYOUT, 30) == []
    assert read_examples(sheet_with(3), LAYOUT, 0) == []


def test_blank_rows_are_not_examples() -> None:
    worksheet = FakeWorksheet(
        [HEADER, ["01/10", "$5", "Food", "A"], [], ["03/10", "$7", "Food", "B"]]
    )
    assert [row.description for row in read_examples(worksheet, LAYOUT, 30)] == ["A", "B"]


def test_columns_can_be_anywhere_and_other_columns_are_ignored() -> None:
    rows = [
        ["Notes", "Category", "Date", "", "Description", "Amount"],
        ["private", "Food", "01/10/2026", "other", "Market", "$5"],
    ]
    layout = Layout(date=3, amount=6, category=2, description=5)
    expected = DisplayedRow(2, "01/10/2026", "$5", "Food", "Market")
    assert read_row(FakeWorksheet(rows), layout, 2) == expected


def test_cells_the_api_leaves_out_read_as_empty_text() -> None:
    worksheet = FakeWorksheet([HEADER, ["01/10/2026", "$5"]])
    assert read_row(worksheet, LAYOUT, 2) == DisplayedRow(2, "01/10/2026", "$5", "", "")
    assert read_row(worksheet, LAYOUT, 9) == DisplayedRow(9, "", "", "", "")
