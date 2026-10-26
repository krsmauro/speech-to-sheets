from speech_to_sheets.sheets.errors import WriteError
from speech_to_sheets.sheets.rows import DisplayedRow

# The fixed replies written in code. They stay English (see the README, Design decisions);
# Claude writes its own questions in the user's language.

# Every confirmation starts with this, and a thread that holds one is never logged again.
LOGGED_PREFIX = "Logged in row"

ALREADY_LOGGED = (
    "This expense is already in the sheet, so nothing new was logged. To change it, edit the"
    " sheet. For another expense, send a new message instead of replying here."
)
NO_SPEECH = "I could not hear any speech in that voice note. Record it again or type it."
UNREADABLE_PHOTO = "I could not read that photo. Send it as a JPEG or PNG, or type the expense."
UNSUPPORTED_FILE = "I can read text, voice notes and photos, but not that kind of file."
NOTHING_TO_READ = "I found nothing to read in that message. Send text, a voice note or a photo."
UNEXPECTED = (
    "Something went wrong (details in the bot's log), so this may not be logged."
    " Check the sheet before sending it again."
)


def logged(row: DisplayedRow) -> str:
    """The row as the sheet shows it, read back after the write."""
    cells = f"{row.date} | {row.amount} | {row.category} | {row.description}"
    return f"{LOGGED_PREFIX} {row.row}: {cells}"


def logged_unread(row: int, error: Exception) -> str:
    return f"{LOGGED_PREFIX} {row}, but I could not read it back to show it: {error}"


def failed(error: Exception) -> str:
    if isinstance(error, WriteError):
        return (
            f"Writing to the sheet failed: {error}\nThe row may have been written anyway, so"
            " check the sheet before trying again."
        )
    return f"Not logged: {error}\nReply here to try again."
