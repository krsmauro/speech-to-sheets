import gspread
from gspread.utils import absolute_range_name, rowcol_to_a1

from speech_to_sheets.sheets.errors import SheetsError, google_errors

FIRST_DATA_ROW = 2
FIELDS = "sheets.data.rowData.values.dataValidation"


def read_categories(worksheet: gspread.Worksheet, column: int, fallback: list[str]) -> list[str]:
    """The options of the category dropdown, read fresh on every message from the first data
    row. Falls back to sheets.fallback_categories when that cell has no readable dropdown."""
    cell = absolute_range_name(worksheet.title, rowcol_to_a1(FIRST_DATA_ROW, column))
    with google_errors("reading the category dropdown"):
        metadata = worksheet.spreadsheet.fetch_sheet_metadata({"ranges": cell, "fields": FIELDS})
        options = _options(worksheet, _condition(metadata))
    if options:
        return options
    if fallback:
        return fallback
    raise SheetsError(
        f"the category column has no dropdown in row {FIRST_DATA_ROW} and"
        " sheets.fallback_categories is empty: add a dropdown or list the categories in config.yaml"
    )


def _condition(metadata: dict) -> dict:
    try:
        cell = metadata["sheets"][0]["data"][0]["rowData"][0]["values"][0]
    except (KeyError, IndexError):
        return {}
    return cell.get("dataValidation", {}).get("condition", {})


def _options(worksheet: gspread.Worksheet, condition: dict) -> list[str]:
    values = [value.get("userEnteredValue", "") for value in condition.get("values", [])]
    if condition.get("type") == "ONE_OF_LIST":
        return _clean(values)
    if condition.get("type") == "ONE_OF_RANGE" and values:
        return _clean(_read_range(worksheet, values[0]))
    return []


def _read_range(worksheet: gspread.Worksheet, formula: str) -> list[str]:
    """A dropdown fed by a range such as =Lists!$A$2:$A$20; with no tab name it is this tab."""
    tab, _, cells = formula.lstrip("=+").strip().rpartition("!")
    cells = cells.replace("$", "")
    range_name = f"{tab}!{cells}" if tab else absolute_range_name(worksheet.title, cells)
    data = worksheet.spreadsheet.values_get(range_name)
    return [cell for row in data.get("values", []) for cell in row]


def _clean(values: list) -> list[str]:
    """Strip spaces, drop blanks and repeats, keep the sheet's order."""
    return list(dict.fromkeys(text for value in values if (text := str(value).strip())))
