import argparse
from pathlib import Path

from speech_to_sheets.cli.init import run_init
from speech_to_sheets.cli.prompts import Prompter
from speech_to_sheets.cli.run import run_bot

COMMANDS = {
    "init": ("create config.yaml by reading your sheet", "file to write"),
    "run": ("start the bot: answer Slack messages until Ctrl-C", "file to read"),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="speech-to-sheets", description="Log expenses from Slack into a Google Sheet."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name, (summary, config_help) in COMMANDS.items():
        command = commands.add_parser(name, help=summary)
        command.add_argument("--config", type=Path, default=Path("config.yaml"), help=config_help)
        command.add_argument("--env", type=Path, default=Path(".env"), help="file with the secrets")
    args = parser.parse_args(argv)
    if args.command == "run":
        return run_bot(args.config, args.env)
    try:
        return run_init(args.config, args.env, Prompter())
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. Nothing written.")
        return 130
