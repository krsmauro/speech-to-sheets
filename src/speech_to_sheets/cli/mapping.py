from speech_to_sheets.cli.guess import guess_columns
from speech_to_sheets.cli.prompts import Prompter
from speech_to_sheets.config.columns import Columns
from speech_to_sheets.sheets.errors import SheetsError
from speech_to_sheets.sheets.sample import ColumnSample
from speech_to_sheets.sheets.schema import Layout, column_letter, find_layout

ROLES = ("date", "amount", "category", "description")


def confirm_columns(prompt: Prompter, samples: list[ColumnSample]) -> tuple[Columns, Layout]:
    """Propose a column for each role, let the user accept or pick each one, then check the
    result the same way the bot reads the sheet."""
    named = [sample for sample in samples if sample.header]
    if len(named) < len(ROLES):
        found = ", ".join(_label(sample) for sample in named) or "none"
        raise SheetsError(f"row 1 needs a header for each of {', '.join(ROLES)}; found: {found}")
    prompt.say("Headers in row 1: " + ", ".join(_label(sample) for sample in named))
    guess = guess_columns(samples)
    if len(guess) == len(ROLES):
        prompt.say("Proposed columns:")
        for role in ROLES:
            prompt.say(f"  {role + ':':<13}{_label(_by_column(named, guess[role]))}")
        if prompt.confirm("Use these columns?", default=True):
            return _checked(samples, guess)
    else:
        prompt.say("Could not guess every column. Pick them below.")
    picks: dict[str, int] = {}
    for role in ROLES:
        options = [sample for sample in named if sample.column not in picks.values()]
        columns = [sample.column for sample in options]
        default = columns.index(guess[role]) if guess.get(role) in columns else None
        index = prompt.choose(f"Which column holds the {role}?", _labels(options), default)
        picks[role] = options[index].column
    return _checked(samples, picks)


def _checked(samples: list[ColumnSample], picks: dict[str, int]) -> tuple[Columns, Layout]:
    """The bot finds columns by header text, so a picked header must be unique in row 1."""
    headers = [sample.header for sample in samples]  # read_samples covers columns 1, 2, 3...
    folded = [header.casefold() for header in headers]
    for column in picks.values():
        header = headers[column - 1]
        if folded.count(header.casefold()) > 1:
            raise SheetsError(
                f"the header {header!r} is in more than one column; the bot finds columns by"
                " header text, so rename one of them in the sheet and run init again"
            )
    columns = Columns(**{role: headers[column - 1] for role, column in picks.items()})
    return columns, find_layout(headers, columns)


def _by_column(samples: list[ColumnSample], column: int) -> ColumnSample:
    return next(sample for sample in samples if sample.column == column)


def _label(sample: ColumnSample) -> str:
    return f"{column_letter(sample.column)} {sample.header}"


def _labels(samples: list[ColumnSample]) -> list[str]:
    return [_label(sample) for sample in samples]
