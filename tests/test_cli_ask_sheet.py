from pathlib import Path

from speech_to_sheets.cli.ask_sheet import (
    ask_categories,
    ask_spreadsheet,
    choose_tab,
    sheet_id_from,
)
from tests.fake_book import FakeBook, choice, text
from tests.scripted import Script

URL = "https://docs.google.com/spreadsheets/d/1aB-c_9/edit?gid=0#gid=0"


def test_sheet_id_from_a_browser_url_or_a_bare_id() -> None:
    assert sheet_id_from(URL) == "1aB-c_9"
    assert sheet_id_from("1aB-c_9") == "1aB-c_9"


def test_ask_spreadsheet_repeats_until_the_answer_holds_an_id_then_opens_it() -> None:
    book = FakeBook({"Expenses": []})
    opened = []
    script = Script("", "https://example.com/nothing", URL)
    result = ask_spreadsheet(script.prompter, Path("key.json"), lambda *a: opened.append(a) or book)
    assert result is book
    assert opened == [(Path("key.json"), "1aB-c_9")]
    assert script.said == ["Paste the sheet's address from the browser, or just its ID."] * 2 + [
        "Opened Household."
    ]


def test_choose_tab_asks_when_there_are_several() -> None:
    book = FakeBook({"Summary": [], "Expenses": []})
    script = Script("2")
    assert choose_tab(script.prompter, book).title == "Expenses"


def test_choose_tab_takes_the_only_tab_without_asking() -> None:
    script = Script()
    assert choose_tab(script.prompter, FakeBook({"Expenses": []})).title == "Expenses"
    assert script.said == ["Using its only tab, Expenses."]


def test_a_readable_dropdown_needs_no_fallback() -> None:
    rows = [[text("Kind")], [choice("Food", ["Food", "Transport"])]]
    script = Script()
    assert ask_categories(script.prompter, FakeBook({"Expenses": rows}).tabs[0], 1) == []
    assert script.said == ["Categories from the dropdown (2): Food, Transport"]


def test_without_a_dropdown_the_user_types_the_categories() -> None:
    rows = [[text("Kind")], [text("Food")]]
    script = Script(" , ", "Food, Transport ,Food,, Café")
    tab = FakeBook({"Expenses": rows}).tabs[0]
    assert ask_categories(script.prompter, tab, 1) == ["Food", "Transport", "Café"]
    assert script.said[0].startswith("Could not read a category dropdown: ")
    assert "Type at least one category." in script.said
