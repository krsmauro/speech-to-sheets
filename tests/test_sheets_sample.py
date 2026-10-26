from speech_to_sheets.sheets.sample import FIELDS, ColumnSample, read_samples
from tests.fake_book import FakeBook, choice, date, number, text

HEADERS = [text("When"), text("Paid"), text("Kind"), text("Details")]


def samples_of(rows: list[list[dict]]) -> list[ColumnSample]:
    return read_samples(FakeBook({"Expenses": rows}).tabs[0], rows=20)


def test_counts_what_each_column_holds() -> None:
    rows = [
        HEADERS,
        [date(46000), number(12.5), choice("Food", ["Food"]), text("Market")],
        [date(46001), number(30, "NUMBER"), choice("Food", ["Food"]), text("Bakery")],
        [{}, {}, choice("", ["Food"])],  # a dropdown that covers empty rows too
    ]
    assert samples_of(rows) == [
        ColumnSample(1, "When", dates=2),
        ColumnSample(2, "Paid", numbers=2),
        ColumnSample(3, "Kind", dropdowns=3, texts=["Food", "Food"]),
        ColumnSample(4, "Details", texts=["Market", "Bakery"]),
    ]


def test_one_request_for_the_header_and_the_first_rows() -> None:
    book = FakeBook({"Expenses": [HEADERS]})
    read_samples(book.tabs[0], rows=20)
    assert book.requests == [{"ranges": "'Expenses'!1:21", "fields": FIELDS}]


def test_a_date_time_is_a_date_and_an_unformatted_number_is_a_number() -> None:
    timestamp = date(46000.5)
    timestamp["effectiveFormat"]["numberFormat"]["type"] = "DATE_TIME"
    rows = [[text("A"), text("B")], [timestamp, {"effectiveValue": {"numberValue": 7}}]]
    assert samples_of(rows) == [ColumnSample(1, "A", dates=1), ColumnSample(2, "B", numbers=1)]


def test_headers_are_trimmed_and_columns_after_the_last_header_are_ignored() -> None:
    rows = [
        [text(" When "), {}, text("Details"), text("  ")],
        [date(46000), text("stray"), text("Market"), text("x"), text("far right")],
    ]
    assert samples_of(rows) == [
        ColumnSample(1, "When", dates=1),
        ColumnSample(2, "", texts=["stray"]),  # kept, so column numbers stay right
        ColumnSample(3, "Details", texts=["Market"]),
    ]


def test_an_empty_tab_has_no_samples() -> None:
    assert samples_of([]) == []
