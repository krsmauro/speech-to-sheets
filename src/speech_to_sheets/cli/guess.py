from collections.abc import Callable

from speech_to_sheets.config.columns import Columns
from speech_to_sheets.sheets.sample import ColumnSample

# How well a column fits each role, judged by its cells, so any header language works.
# The order matters: each column goes to one role, the first role that claims it.
SCORES: dict[str, Callable[[ColumnSample], int]] = {
    "date": lambda sample: sample.dates,
    "amount": lambda sample: sample.numbers,
    "category": lambda sample: sample.dropdowns,
    # Free text with the most different values; a dropdown column is a category, not this.
    "description": lambda sample: 0 if sample.dropdowns else len(set(sample.texts)),
}


def guess_columns(samples: list[ColumnSample]) -> dict[str, int]:
    """A proposed column number for each role it can guess. The user confirms or corrects it.

    A header equal to the English default name (Date, Amount, ...) wins; otherwise the
    content decides: dates, other numbers, a dropdown, varied text. No word lists.
    """
    named = {sample.header.casefold(): sample.column for sample in samples if sample.header}
    guess = {
        role: named[header.casefold()]
        for role, header in Columns().model_dump().items()
        if header.casefold() in named
    }
    free = [s for s in samples if s.header and s.column not in guess.values()]
    for role, score in SCORES.items():
        if role in guess:
            continue
        best = max(free, key=score, default=None)  # on a tie, max keeps the leftmost
        if best is not None and score(best) > 0:
            guess[role] = best.column
            free.remove(best)
    return guess
