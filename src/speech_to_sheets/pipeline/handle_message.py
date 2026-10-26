import logging
import threading

from slack_sdk import WebClient

from speech_to_sheets.dedupe.errors import DedupeError
from speech_to_sheets.extract.client import extract
from speech_to_sheets.extract.errors import ExtractError
from speech_to_sheets.extract.sanity import check
from speech_to_sheets.extract.schema import NeedsInfo
from speech_to_sheets.pipeline import texts
from speech_to_sheets.pipeline.bundle import bundle
from speech_to_sheets.pipeline.log_entry import log_entry
from speech_to_sheets.pipeline.logged import already_logged
from speech_to_sheets.pipeline.services import Services
from speech_to_sheets.pipeline.sheet_context import read_context
from speech_to_sheets.sheets.dates import today_in
from speech_to_sheets.sheets.errors import SheetsError
from speech_to_sheets.slack.errors import SlackError
from speech_to_sheets.slack.message import Message, sent_at
from speech_to_sheets.slack.replies import post_reply
from speech_to_sheets.slack.thread import read_thread
from speech_to_sheets.stt.errors import SttError

logger = logging.getLogger(__name__)

# Errors whose message is safe to show in Slack. Anything else is a bug, logged in full.
HANDLED_ERRORS = (DedupeError, ExtractError, SheetsError, SlackError, SttError)

# One message at a time: two quick replies in one thread ("12", then "at the market") would
# otherwise both read the thread and log the expense twice. A household sends a few
# messages a day, so the short wait does not matter.
_one_at_a_time = threading.Lock()


def handle_message(message: Message, slack: WebClient, services: Services) -> None:
    """Answer one direct message from an allowed person, in its thread: log the expense and
    confirm it, or ask for what is missing. A repeat of a handled message gets no answer."""
    with _one_at_a_time:
        try:
            if not services.store.claim(message.message_id):
                logger.info("Message %s was already handled; ignored", message.message_id)
                return
            reply = _answer(message, slack, services)
        except HANDLED_ERRORS as error:
            logger.error("Message %s: %s", message.message_id, error)
            _fail(services, message)
            reply = texts.failed(error)
        except Exception:
            logger.exception("Message %s: unexpected error", message.message_id)
            _fail(services, message)
            reply = texts.UNEXPECTED
        _post(slack, message, reply)


def _answer(message: Message, slack: WebClient, services: Services) -> str:
    thread = _thread(message, slack)
    if already_logged(thread, services.store):
        logger.info("Message %s: its thread is already logged", message.message_id)
        return texts.ALREADY_LOGGED
    parts = bundle(thread, message, services.files)
    if parts.unusable:
        logger.info("Message %s: nothing to read in it", message.message_id)
        return parts.unusable
    sheet = read_context(services.worksheet, services.sheets, services.extract.example_rows)
    # The day the thread started, not the clock: a note sent at 23:55 and handled after
    # midnight keeps its day, and so does a question answered the next morning.
    today = today_in(services.timezone, sent_at(message.thread_root))
    model = services.extract.model
    result = extract(services.claude, parts.request, sheet.categories, sheet.examples, model, today)
    result = check(result, sheet.categories, today)
    if isinstance(result, NeedsInfo):
        logger.info("Message %s: asked a question", message.message_id)
        return result.question
    return log_entry(services, sheet.layout, result, message.message_id)


def _thread(message: Message, slack: WebClient) -> list[Message]:
    """The message's thread, oldest first, the bot's own replies included."""
    if message.thread_ts is None:
        return [message]
    thread = read_thread(slack, message.channel, message.thread_root)
    if all(other.ts != message.ts for other in thread):
        thread.append(message)  # a reply that just arrived may not be listed yet
    return thread


def _fail(services: Services, message: Message) -> None:
    try:
        services.store.fail(message.message_id)
    except DedupeError as error:  # the store itself is broken, or the row was already written
        logger.error("Message %s: %s", message.message_id, error)


def _post(slack: WebClient, message: Message, text: str) -> None:
    try:
        post_reply(slack, message.channel, message.thread_root, text)
    except SlackError as error:
        logger.error("Message %s: could not reply: %s", message.message_id, error)
