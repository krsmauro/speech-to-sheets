import logging
from collections.abc import Collection
from decimal import Decimal

from slack_sdk import WebClient

from speech_to_sheets.dedupe.checkpoint import read_checkpoint, save_checkpoint
from speech_to_sheets.dedupe.lookup import unseen
from speech_to_sheets.pipeline.handle_message import handle_message
from speech_to_sheets.pipeline.services import Services
from speech_to_sheets.slack.allowlist import is_allowed
from speech_to_sheets.slack.history import dm_channels, messages_since
from speech_to_sheets.slack.message import Message

logger = logging.getLogger(__name__)

DAY = 24 * 60 * 60
HOUR = 60 * 60
# Look a little before the last check, so a message Slack listed late is not missed.
# Messages already handled are skipped through the dedupe store.
OVERLAP_SECONDS = 5 * 60
# Replies are looked for in threads started up to this long before the last check.
THREAD_DAYS = 7


def catch_up(
    slack: WebClient,
    services: Services,
    allowed_user_ids: Collection[str],
    retention_days: int,
    now: float,
) -> int:
    """Handle the direct messages the bot missed since it last looked: sent while the
    computer slept or was offline, or an event Slack never delivered. Returns how many.

    The very first time, it only notes the time, so messages sent before the bot ever ran
    are never logged. It never looks back as far as dedupe.retention_days: a message whose
    entry was pruned would count as new and could be logged twice.
    """
    store = services.store
    checkpoint = read_checkpoint(store)
    if checkpoint is None:
        save_checkpoint(store, now)
        logger.info("Catch-up starts now; messages sent before this first start are skipped")
        return 0
    since = _since(checkpoint, now, retention_days)
    missed = _missed(slack, services, allowed_user_ids, since)
    for message in missed:
        handle_message(message, slack, services)
    save_checkpoint(store, now)
    return len(missed)


def _since(checkpoint: float, now: float, retention_days: int) -> float:
    oldest = now - retention_days * DAY + HOUR  # an hour short of the pruning age
    since = checkpoint - OVERLAP_SECONDS
    if since < oldest:
        logger.warning(
            "The bot was off for about %d days or more; older messages are not caught up",
            retention_days,
        )
        return oldest
    return since


def _missed(
    slack: WebClient, services: Services, allowed_user_ids: Collection[str], since: float
) -> list[Message]:
    """People's messages after `since` that the dedupe store never saw, oldest first."""
    threads_since = since - THREAD_DAYS * DAY
    sent = [
        message
        for channel in dm_channels(slack, allowed_user_ids)
        for message in messages_since(slack, channel, since, threads_since)
        if is_allowed(message, allowed_user_ids)
    ]
    new = unseen(services.store, [message.message_id for message in sent])
    missed = [message for message in sent if message.message_id in new]
    return sorted(missed, key=lambda message: Decimal(message.ts))
