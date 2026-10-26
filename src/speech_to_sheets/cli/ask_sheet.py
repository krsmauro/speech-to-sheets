from collections.abc import Callable
from pathlib import Path

import gspread
from gspread.exceptions import NoValidUrlKeyFound
from gspread.utils import extract_id_from_url

from speech_to_sheets.cli.prompts import Prompter
from speech_to_sheets.sheets.categories import read_categories
from speech_to_sheets.sheets.client import list_tabs
from speech_to_sheets.sheets.errors import SheetsError

OpenSpreadsheet = Callable[[Path, str], gspread.Spreadsheet]


def ask_spreadsheet(
    prompt: Prompter, key_file: Path, open_book: OpenSpreadsheet
) -> gspread.Spreadsheet:
    """Ask for the sheet's URL (or bare ID) and open it with the service account."""
    answer = prompt.ask("Sheet URL or ID", check=_url_problem)
    spreadsheet = open_book(key_file, sheet_id_from(answer))
    prompt.say(f"Opened {spreadsheet.title}.")
    return spreadsheet


def sheet_id_from(text: str) -> str:
    """The ID in a pasted browser URL, or the text itself when it is already an ID."""
    return extract_id_from_url(text) if "/" in text else text


def choose_tab(prompt: Prompter, spreadsheet: gspread.Spreadsheet) -> gspread.Worksheet:
    tabs = list_tabs(spreadsheet)
    if len(tabs) == 1:
        prompt.say(f"Using its only tab, {tabs[0].title}.")
        return tabs[0]
    return tabs[prompt.choose("Which tab holds the expenses?", [tab.title for tab in tabs])]


def ask_categories(prompt: Prompter, worksheet: gspread.Worksheet, column: int) -> list[str]:
    """The fallback category list for config.yaml: empty when the dropdown is readable,
    because the bot reads the dropdown itself on every message."""
    try:
        options = read_categories(worksheet, column, [])
    except SheetsError as error:
        prompt.say(f"Could not read a category dropdown: {error}")
        prompt.say("Type the categories instead, spelled exactly as in the sheet.")
        answer = prompt.ask("Categories, separated by commas", check=_list_problem)
        return _split(answer)
    prompt.say(f"Categories from the dropdown ({len(options)}): {', '.join(options)}")
    return []


def _url_problem(answer: str) -> str | None:
    try:
        if answer and sheet_id_from(answer):
            return None
    except NoValidUrlKeyFound:
        pass
    return "Paste the sheet's address from the browser, or just its ID."


def _list_problem(answer: str) -> str | None:
    return None if _split(answer) else "Type at least one category."


def _split(answer: str) -> list[str]:
    """Comma separated, spaces trimmed, blanks and repeats dropped, order kept."""
    return list(dict.fromkeys(item.strip() for item in answer.split(",") if item.strip()))
