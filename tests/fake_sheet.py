import json
import time

import requests
from gspread.exceptions import APIError
from gspread.utils import a1_range_to_grid_range


class FakeSpreadsheet:
    """Stands in for gspread.Spreadsheet: canned metadata and ranges; records each request."""

    def __init__(self, metadata: dict | None = None, ranges: dict | None = None) -> None:
        self.metadata = metadata or {}
        self.ranges = ranges or {}
        self.requests: list = []
        self.updates: list = []
        self.worksheet: FakeWorksheet | None = None

    def fetch_sheet_metadata(self, params: dict | None = None) -> dict:
        self.requests.append(params)
        return self.metadata

    def values_get(self, range_name: str, params: dict | None = None) -> dict:
        self.requests.append(range_name)
        return {"values": self.ranges[range_name]}

    def batch_update(self, body: dict) -> dict:
        """Applies updateCells values to the worksheet's grid (start indexes are zero-based)."""
        self.updates.append(body)
        for request in body["requests"]:
            update = request["updateCells"]
            start = update["start"]
            [value] = update["rows"][0]["values"][0]["userEnteredValue"].values()
            self.worksheet.cells[(start["rowIndex"] + 1, start["columnIndex"] + 1)] = value
        return {}


class FakeWorksheet:
    """Stands in for gspread.Worksheet: cell values keyed by 1-based (row, column).

    Like the API, reads leave out trailing empty rows and trailing empty cells.
    """

    title = "Expenses"
    id = 7

    def __init__(
        self, rows: list[list], spreadsheet: FakeSpreadsheet | None = None, delay: float = 0
    ) -> None:
        self.cells = {
            (r, c): value
            for r, row in enumerate(rows, 1)
            for c, value in enumerate(row, 1)
            if value not in (None, "")
        }
        self.spreadsheet = spreadsheet or FakeSpreadsheet()
        self.spreadsheet.worksheet = self
        self.delay = delay

    def row_values(self, row: int) -> list:
        block = self._block(row, row, 1, self._size(1))
        return block[0] if block else []

    def col_values(self, col: int) -> list:
        values = [cells[0] if cells else "" for cells in self._block(1, self._size(0), col, col)]
        time.sleep(self.delay)  # a slow reply: another writer could fill the row meanwhile
        return values

    def get(self, range_name: str, value_render_option: str | None = None) -> list[list]:
        grid = a1_range_to_grid_range(range_name)
        return self._block(
            grid["startRowIndex"] + 1,
            grid["endRowIndex"],
            grid["startColumnIndex"] + 1,
            grid["endColumnIndex"],
        )

    def _block(self, top: int, bottom: int, left: int, right: int) -> list[list]:
        columns = range(left, right + 1)
        rows = [
            _trim([self.cells.get((r, c), "") for c in columns]) for r in range(top, bottom + 1)
        ]
        return _trim(rows)

    def _size(self, axis: int) -> int:
        return max((key[axis] for key in self.cells), default=0)


def _trim(items: list) -> list:
    while items and items[-1] in ("", []):
        items = items[:-1]
    return items


def api_error(code: int, message: str) -> APIError:
    response = requests.Response()
    response.status_code = code
    response._content = json.dumps({"error": {"code": code, "message": message}}).encode()
    return APIError(response)
