from dataclasses import dataclass, field

import gspread
from gspread.utils import absolute_range_name

from speech_to_sheets.sheets.errors import google_errors

FIELDS = (
    "sheets.data.rowData.values(formattedValue,effectiveValue,"
    "effectiveFormat.numberFormat.type,dataValidation.condition.type)"
)
DATE_TYPES = ("DATE", "DATE_TIME")
DROPDOWN_TYPES = ("ONE_OF_LIST", "ONE_OF_RANGE")


@dataclass
class ColumnSample:
    """A column's header and what its first data cells hold, used to guess its role."""

    column: int
    header: str
    dates: int = 0
    numbers: int = 0
    dropdowns: int = 0
    texts: list[str] = field(default_factory=list)


def read_samples(worksheet: gspread.Worksheet, rows: int = 20) -> list[ColumnSample]:
    """Row 1 and the next `rows` rows, in one request. One sample per column, up to the last
    header; columns with no header are kept (with an empty header) so numbers stay right."""
    span = absolute_range_name(worksheet.title, f"1:{rows + 1}")
    with google_errors("reading the first rows"):
        metadata = worksheet.spreadsheet.fetch_sheet_metadata({"ranges": span, "fields": FIELDS})
    try:
        grid = [row.get("values", []) for row in metadata["sheets"][0]["data"][0]["rowData"]]
    except (KeyError, IndexError):
        return []
    headers = [str(cell.get("formattedValue", "")).strip() for cell in grid[0]] if grid else []
    while headers and not headers[-1]:
        headers.pop()
    samples = [ColumnSample(index + 1, header) for index, header in enumerate(headers)]
    for row in grid[1:]:
        for sample, cell in zip(samples, row):
            _count(sample, cell)
    return samples


def _count(sample: ColumnSample, cell: dict) -> None:
    value = cell.get("effectiveValue", {})
    if cell.get("dataValidation", {}).get("condition", {}).get("type") in DROPDOWN_TYPES:
        sample.dropdowns += 1
    if "numberValue" in value:
        number_type = cell.get("effectiveFormat", {}).get("numberFormat", {}).get("type")
        if number_type in DATE_TYPES:
            sample.dates += 1
        else:
            sample.numbers += 1
    elif text := str(value.get("stringValue", "")).strip():
        sample.texts.append(text)
