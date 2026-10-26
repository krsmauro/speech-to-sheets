from gspread.utils import a1_range_to_grid_range, absolute_range_name

# Cells are dicts shaped like the Sheets API's CellData, as seen live on 2026-10-25.


def date(serial: int) -> dict:
    """A date: a serial number with a date format."""
    return {
        "effectiveValue": {"numberValue": serial},
        "effectiveFormat": {"numberFormat": {"type": "DATE"}},
    }


def number(value: float, kind: str = "CURRENCY") -> dict:
    return {
        "effectiveValue": {"numberValue": value},
        "effectiveFormat": {"numberFormat": {"type": kind}},
    }


def text(value: str) -> dict:
    return {"effectiveValue": {"stringValue": value}, "formattedValue": value}


def choice(value: str, options: list[str]) -> dict:
    """A cell with a dropdown (ONE_OF_LIST data validation)."""
    condition = {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": o} for o in options]}
    return {**text(value), "dataValidation": {"condition": condition}}


class FakeTab:
    """Stands in for gspread.Worksheet."""

    def __init__(self, book: "FakeBook", title: str, rows: list[list[dict]], sheet_id: int):
        self.spreadsheet = book
        self.title = title
        self.rows = rows
        self.id = sheet_id


class FakeBook:
    """Stands in for gspread.Spreadsheet. Metadata requests return the cells of one range."""

    id = "sheet-123"
    title = "Household"

    def __init__(self, tabs: dict[str, list[list[dict]]]) -> None:
        self.tabs = [FakeTab(self, name, rows, n) for n, (name, rows) in enumerate(tabs.items())]
        self.requests: list[dict] = []

    def worksheets(self) -> list[FakeTab]:
        return self.tabs

    def fetch_sheet_metadata(self, params: dict) -> dict:
        self.requests.append(params)
        name = params["ranges"]
        tab = next(t for t in self.tabs if name.startswith(absolute_range_name(t.title, "")))
        grid = a1_range_to_grid_range(name.rpartition("!")[2])
        rows = tab.rows[grid.get("startRowIndex", 0) : grid.get("endRowIndex")]
        left, right = grid.get("startColumnIndex", 0), grid.get("endColumnIndex")
        row_data = [{"values": row[left:right]} if row[left:right] else {} for row in rows]
        return {"sheets": [{"data": [{"rowData": row_data}]}]}
