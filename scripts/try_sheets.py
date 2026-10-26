"""Check the Google Sheets connection with the settings in config.yaml and .env.

Read-only unless --append is given. Use the duplicate sheet: --append writes a real row.

    uv run python scripts/try_sheets.py           # columns, dropdown categories, last rows
    uv run python scripts/try_sheets.py --append  # also writes one test row and reads it back

Needs GOOGLE_SERVICE_ACCOUNT_FILE (environment or .env) and the sheets section of config.yaml.
--config and --env point at other files.
"""

import argparse
import sys
from decimal import Decimal
from pathlib import Path

import yaml
from pydantic import ValidationError

from speech_to_sheets.config.env import google_key_file
from speech_to_sheets.config.errors import ConfigError, describe
from speech_to_sheets.config.sections import SheetsConfig
from speech_to_sheets.sheets.append import append_entry
from speech_to_sheets.sheets.categories import read_categories
from speech_to_sheets.sheets.client import open_worksheet
from speech_to_sheets.sheets.dates import today_in
from speech_to_sheets.sheets.errors import SheetsError
from speech_to_sheets.sheets.examples import read_examples
from speech_to_sheets.sheets.read_row import read_row
from speech_to_sheets.sheets.schema import read_layout

TEST_DESCRIPTION = "speech-to-sheets test row, delete me"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the Google Sheets connection.")
    parser.add_argument("--append", action="store_true", help="write one test row")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--env", type=Path, default=Path(".env"))
    args = parser.parse_args()
    data = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    try:
        sheets = SheetsConfig.model_validate(data.get("sheets") or {})
        key = google_key_file(args.env)
    except ValidationError as error:
        print(f"{args.config}, sheets section:", *describe(error), sep="\n  ")
        return 2
    except ConfigError as error:
        print(error)
        return 2
    try:
        worksheet = open_worksheet(key, sheets.sheet_id, sheets.tab)
        layout = read_layout(worksheet, sheets.columns)
        print(f"Columns found: {layout}")
        categories = show_categories(worksheet, layout.category, sheets.fallback_categories)
        print("Last rows:")
        for row in read_examples(worksheet, layout, 5):
            print(f"  {row}")
        if args.append:
            day = today_in(data.get("timezone") or "UTC")
            row = append_entry(
                worksheet,
                layout,
                day=day,
                amount=Decimal(1234),
                category=categories[0],
                description=TEST_DESCRIPTION,
            )
            print(f"Wrote row {row}, read back as: {read_row(worksheet, layout, row)}")
            print("Check it in the sheet, then delete that row.")
    except SheetsError as error:
        print(f"Failed: {error}")
        return 1
    return 0


def show_categories(worksheet: object, column: int, fallback: list[str]) -> list[str]:
    """Show whether the dropdown itself is readable, and whether the fallback matches it."""
    try:
        options = read_categories(worksheet, column, [])
    except SheetsError:
        print(f"Dropdown NOT readable; the bot would use fallback_categories: {fallback}")
        return read_categories(worksheet, column, fallback)
    print(f"Dropdown categories ({len(options)}): {options}")
    if fallback and fallback != options:
        print(f"Note: fallback_categories differs from the dropdown: {fallback}")
    return options


if __name__ == "__main__":
    sys.exit(main())
