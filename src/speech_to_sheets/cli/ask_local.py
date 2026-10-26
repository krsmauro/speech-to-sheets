import os
from collections.abc import Callable, Mapping
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from speech_to_sheets.cli.prompts import Prompter
from speech_to_sheets.config.sections import SlackConfig

DEFAULT_MODEL = "models/ggml-large-v3-turbo-q5_0.bin"


def ask_timezone(prompt: Prompter) -> str:
    question = "Timezone for the date of each entry (IANA name, for example Europe/Madrid)"
    return prompt.ask(question, default=local_timezone(), check=_timezone_problem)


def ask_slack_users(prompt: Prompter) -> list[str]:
    """Optional here: the Slack app may not exist yet. The bot will not start without one."""
    prompt.say("Who may use the bot? Everyone else is ignored. To find a member ID in Slack,")
    prompt.say("open the person's profile, then More, Copy member ID.")
    question = "Slack member IDs, separated by commas (blank to fill in later)"
    return _member_ids(prompt.ask(question, check=_member_ids_problem))


def ask_model_path(prompt: Prompter) -> str:
    path = prompt.ask("whisper.cpp model file", default=DEFAULT_MODEL)
    if not Path(path).expanduser().is_file():
        prompt.say(f"Note: {path} does not exist yet; config.example.yaml shows how to get it.")
    return path


def ask_language(prompt: Prompter) -> str:
    question = "Language of your voice notes, for example en or es (auto lets whisper detect it)"
    return prompt.ask(question, default="auto")


def local_timezone(
    environ: Mapping[str, str] = os.environ, readlink: Callable[[str], str] = os.readlink
) -> str:
    """This machine's IANA timezone name, or UTC when it cannot be told (as on Windows)."""
    name = environ.get("TZ", "").removeprefix(":")
    if not name:
        try:
            # macOS and most Linux systems link /etc/localtime into the zoneinfo folder.
            _, found, name = readlink("/etc/localtime").partition("zoneinfo/")
        except OSError:
            return "UTC"
        if not found:
            return "UTC"
    return "UTC" if _timezone_problem(name) else name


def _timezone_problem(name: str) -> str | None:
    try:
        ZoneInfo(name)
    except (KeyError, ValueError, OSError):
        return "Unknown timezone. Use an IANA name like America/New_York or Europe/Madrid."
    return None


def _member_ids(answer: str) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in answer.split(",") if item.strip()))


def _member_ids_problem(answer: str) -> str | None:
    if not _member_ids(answer):
        return None
    try:
        SlackConfig(allowed_user_ids=_member_ids(answer))
    except ValidationError:
        return "Each member ID starts with U or W followed by capital letters and digits."
    return None
