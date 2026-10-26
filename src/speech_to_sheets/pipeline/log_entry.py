import logging

from speech_to_sheets.dedupe.errors import DedupeError
from speech_to_sheets.extract.schema import Complete
from speech_to_sheets.pipeline import texts
from speech_to_sheets.pipeline.services import Services
from speech_to_sheets.sheets.append import append_entry
from speech_to_sheets.sheets.errors import SheetsError
from speech_to_sheets.sheets.read_row import read_row
from speech_to_sheets.sheets.schema import Layout

logger = logging.getLogger(__name__)


def log_entry(services: Services, layout: Layout, entry: Complete, message_id: str) -> str:
    """Write the entry, mark the message done and return the confirmation, which shows the
    row as the sheet stores it.

    Only the write can raise. Once Google has the row, later problems go into the reply
    instead, so the user is never told it failed when it is in the sheet.
    """
    row = append_entry(
        services.worksheet,
        layout,
        day=entry.day,
        amount=entry.amount,
        category=entry.category,
        description=entry.description,
    )
    logger.info("Message %s: logged in row %d", message_id, row)
    try:
        services.store.finish(message_id, row)
    except DedupeError as error:
        # The confirmation posted below still marks the thread as logged.
        logger.error("Row %d is written, but the dedupe store failed: %s", row, error)
    try:
        return texts.logged(read_row(services.worksheet, layout, row))
    except SheetsError as error:
        return texts.logged_unread(row, error)
