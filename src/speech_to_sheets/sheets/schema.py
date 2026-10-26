from dataclasses import dataclass

import gspread
from gspread.utils import rowcol_to_a1

from speech_to_sheets.config.columns import Columns
from speech_to_sheets.sheets.errors import SheetsError, google_errors


@dataclass(frozen=True)
class Layout:
    """The 1-based column number of each role, found by its header text in row 1."""

    date: int
    amount: int
    category: int
    description: int


def read_layout(worksheet: gspread.Worksheet, columns: Columns) -> Layout:
    """Read row 1 fresh on every message, so moving or adding columns never breaks a write."""
    with google_errors("reading the headers in row 1"):
        headers = worksheet.row_values(1)
    return find_layout(headers, columns)


def find_layout(headers: list[str | None], columns: Columns) -> Layout:
    """Match each configured header, ignoring case and surrounding spaces. Lists every problem."""
    found = [(header or "").strip().casefold() for header in headers]
    numbers: dict[str, int] = {}
    problems = []
    for role, wanted in columns.model_dump().items():
        matches = [index + 1 for index, header in enumerate(found) if header == wanted.casefold()]
        if len(matches) == 1:
            numbers[role] = matches[0]
        elif not matches:
            problems.append(f"sheets.columns.{role}: no header {wanted!r} in row 1")
        else:
            letters = ", ".join(column_letter(number) for number in matches)
            problems.append(f"sheets.columns.{role}: header {wanted!r} is in columns {letters}")
    if problems:
        shown = ", ".join(header.strip() for header in headers if header and header.strip())
        problems.append(f"Headers found in row 1: {shown or 'none'}")
        raise SheetsError("\n".join(problems))
    return Layout(**numbers)


def column_letter(column: int) -> str:
    return rowcol_to_a1(1, column).removesuffix("1")
