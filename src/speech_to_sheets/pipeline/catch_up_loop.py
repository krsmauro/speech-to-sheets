import logging
import threading
import time
from collections.abc import Callable, Collection

from slack_sdk import WebClient

from speech_to_sheets.dedupe.errors import DedupeError
from speech_to_sheets.pipeline.catch_up import catch_up
from speech_to_sheets.pipeline.services import Services
from speech_to_sheets.slack.errors import SlackError
from speech_to_sheets.slack.history import dm_channels

logger = logging.getLogger(__name__)

# A Mac that sleeps keeps the bot running but loses the events Slack sent meanwhile, so
# catch-up runs on a timer, not only at startup. A round with nothing missed is two or
# three cheap Slack requests.
INTERVAL_SECONDS = 5 * 60


def start_catch_up(
    slack: WebClient,
    services: Services,
    allowed_user_ids: Collection[str],
    retention_days: int,
    stop: threading.Event | None = None,
    clock: Callable[[], float] = time.time,
) -> threading.Thread:
    """Look for missed messages now and then every few minutes, on a background thread.

    First checks that Slack lets the bot list its direct messages, so a missing im:read
    scope stops the bot at startup (SlackError) instead of failing quietly later.
    """
    dm_channels(slack, allowed_user_ids)
    stop = stop or threading.Event()

    def rounds() -> None:
        while True:
            _round(slack, services, allowed_user_ids, retention_days, clock())
            if stop.wait(INTERVAL_SECONDS):
                return

    thread = threading.Thread(target=rounds, name="catch-up", daemon=True)
    thread.start()
    return thread


def _round(
    slack: WebClient,
    services: Services,
    allowed_user_ids: Collection[str],
    retention_days: int,
    now: float,
) -> None:
    """One look for missed messages. A failure is logged and tried again next round."""
    try:
        count = catch_up(slack, services, allowed_user_ids, retention_days, now)
    except (SlackError, DedupeError) as error:
        logger.warning("Catch-up failed, next try in %d minutes: %s", INTERVAL_SECONDS // 60, error)
        return
    except Exception:
        logger.exception("Catch-up: unexpected error")
        return
    if count:
        logger.info("Catch-up handled %d missed message(s)", count)
