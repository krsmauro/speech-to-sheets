import logging

from speech_to_sheets.config.settings import Settings
from speech_to_sheets.dedupe.prune import prune
from speech_to_sheets.dedupe.store import DedupeStore
from speech_to_sheets.extract.check import check_model
from speech_to_sheets.extract.client import make_client
from speech_to_sheets.pipeline.files import SlackFileReader
from speech_to_sheets.pipeline.services import Services
from speech_to_sheets.pipeline.sheet_context import read_context
from speech_to_sheets.sheets.client import open_worksheet
from speech_to_sheets.stt.check import check_stt

logger = logging.getLogger(__name__)


def open_services(settings: Settings) -> Services:
    """Check and open everything once, so a setup problem stops the bot at startup with a
    clear message instead of failing on the first expense. Raises the module's own error
    (SttError, DedupeError, SheetsError, ExtractError)."""
    check_stt(settings.stt)
    store = DedupeStore(settings.dedupe.path)
    pruned = prune(store, settings.dedupe.retention_days)
    logger.info("Dedupe store %s ready; %d old entries removed", settings.dedupe.path, pruned)
    secrets = settings.secrets
    worksheet = open_worksheet(
        secrets.google_key_file, settings.sheets.sheet_id, settings.sheets.tab
    )
    sheet = read_context(worksheet, settings.sheets, rows=0)  # headers and categories
    logger.info("Sheet ready: columns %s, %d categories", sheet.layout, len(sheet.categories))
    claude = make_client(secrets.anthropic_api_key.get_secret_value())
    check_model(claude, settings.extract.model)
    logger.info("Anthropic key and model %s accepted", settings.extract.model)
    return Services(
        worksheet=worksheet,
        store=store,
        claude=claude,
        files=SlackFileReader(secrets.slack_bot_token.get_secret_value(), settings.stt),
        sheets=settings.sheets,
        extract=settings.extract,
        timezone=settings.timezone,
    )
