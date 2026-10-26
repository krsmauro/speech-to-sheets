from pathlib import Path

from speech_to_sheets.cli.ask_local import (
    ask_language,
    ask_model_path,
    ask_slack_users,
    ask_timezone,
)
from speech_to_sheets.cli.ask_sheet import (
    OpenSpreadsheet,
    ask_categories,
    ask_spreadsheet,
    choose_tab,
)
from speech_to_sheets.cli.mapping import confirm_columns
from speech_to_sheets.cli.prompts import Prompter
from speech_to_sheets.cli.write_config import write_config
from speech_to_sheets.config.env import google_key_file
from speech_to_sheets.config.errors import ConfigError
from speech_to_sheets.sheets.client import open_spreadsheet
from speech_to_sheets.sheets.errors import SheetsError
from speech_to_sheets.sheets.sample import read_samples


def run_init(
    config_path: Path,
    env_file: Path,
    prompt: Prompter,
    open_book: OpenSpreadsheet = open_spreadsheet,
) -> int:
    """Create config.yaml by reading the sheet. Writes only at the very end. Returns the exit
    code. Needs only the Google key from the secrets, so it works before Slack is set up."""
    try:
        key_file = google_key_file(env_file)
    except ConfigError as error:
        prompt.say(f"Failed: {error}")
        return 1
    replace = config_path.exists()
    if replace and not prompt.confirm(f"{config_path} already exists. Replace it?", False):
        prompt.say("Nothing written.")
        return 1
    try:
        spreadsheet = ask_spreadsheet(prompt, key_file, open_book)
        worksheet = choose_tab(prompt, spreadsheet)
        columns, layout = confirm_columns(prompt, read_samples(worksheet))
        fallback = ask_categories(prompt, worksheet, layout.category)
    except SheetsError as error:
        prompt.say(f"Failed: {error}")
        prompt.say("Nothing written.")
        return 1
    timezone = ask_timezone(prompt)
    member_ids = ask_slack_users(prompt)
    model_path = ask_model_path(prompt)
    language = ask_language(prompt)
    data = {
        "timezone": timezone,
        "slack": {"allowed_user_ids": member_ids},
        "sheets": {
            "sheet_id": spreadsheet.id,
            "tab": worksheet.title,
            "columns": columns.model_dump(),
            "fallback_categories": fallback,
        },
        "stt": {"model_path": model_path, "language": language},
    }
    try:
        write_config(config_path, data, overwrite=replace)
    except OSError as error:
        prompt.say(f"Could not write {config_path}: {error}")
        return 1
    prompt.say(f"Wrote {config_path}. To check it, run:")
    prompt.say(f"  uv run python scripts/try_sheets.py --config {config_path}")
    if not member_ids:
        prompt.say("Before starting the bot, list the member IDs in slack.allowed_user_ids.")
    return 0
