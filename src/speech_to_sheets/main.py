import argparse
from pathlib import Path

from speech_to_sheets.cli.init import run_init
from speech_to_sheets.cli.prompts import Prompter


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="speech-to-sheets", description="Log expenses from Slack into a Google Sheet."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create config.yaml by reading your sheet")
    init.add_argument("--config", type=Path, default=Path("config.yaml"), help="file to write")
    init.add_argument("--env", type=Path, default=Path(".env"), help="file with the secrets")
    args = parser.parse_args(argv)
    try:
        return run_init(args.config, args.env, Prompter())
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. Nothing written.")
        return 130
