import logging
import sys
from pathlib import Path

from speech_to_sheets.config.errors import ConfigError
from speech_to_sheets.config.settings import load_settings
from speech_to_sheets.dedupe.errors import DedupeError
from speech_to_sheets.extract.errors import ExtractError
from speech_to_sheets.pipeline.catch_up_loop import start_catch_up
from speech_to_sheets.pipeline.handle_message import handle_message
from speech_to_sheets.pipeline.startup import open_services
from speech_to_sheets.sheets.errors import SheetsError
from speech_to_sheets.slack.client import build_app, run
from speech_to_sheets.slack.errors import SlackError
from speech_to_sheets.stt.errors import SttError

logger = logging.getLogger(__name__)

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
STARTUP_ERRORS = (ConfigError, DedupeError, ExtractError, SheetsError, SlackError, SttError)


def run_bot(config_path: Path, env_file: Path) -> int:
    """Check the setup, then answer Slack direct messages until stopped. Returns the exit
    code. The log holds message IDs, row numbers and errors, never what people wrote."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    try:
        settings = load_settings(config_path, env_file)
        services = open_services(settings)
        allowed = settings.slack.allowed_user_ids
        app = build_app(
            settings.secrets.slack_bot_token.get_secret_value(),
            allowed,
            lambda message, client: handle_message(message, client, services),
        )
        start_catch_up(app.client, services, allowed, settings.dedupe.retention_days)
        logger.info("Connecting to Slack. Send the bot a direct message; Ctrl-C stops.")
        run(app, settings.secrets.slack_app_token.get_secret_value())
    except STARTUP_ERRORS as error:
        print(f"Not started: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
    return 0
