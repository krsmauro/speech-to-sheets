"""A small expense sheet for the init tests. Header names are deliberately not the defaults,
so the column guess has to come from the cells."""

from tests.fake_book import FakeBook, choice, date, number, text

URL = "https://docs.google.com/spreadsheets/d/sheet-123/edit"
OPTIONS = ["Food", "Transport"]


def book(dropdown: bool = True, headers: tuple = ("When", "Paid", "Kind", "Details")) -> FakeBook:
    def kind(value: str) -> dict:
        return choice(value, OPTIONS) if dropdown else text(value)

    rows = [
        [text(header) for header in headers],
        [date(46000), number(12.5), kind("Food"), text("Market")],
        [date(46001), number(3), kind("Transport"), text("Bus")],
        [date(46001), number(8), kind("Food"), text("Bakery")],
    ]
    return FakeBook({"Summary": [[text("Total")]], "Expenses": rows})


def opener(spreadsheet: FakeBook, opened: list) -> object:
    """An open_spreadsheet stand-in that records what it was asked to open."""

    def open_book(key_file: object, sheet_id: str) -> FakeBook:
        opened.append((key_file, sheet_id))
        return spreadsheet

    return open_book
