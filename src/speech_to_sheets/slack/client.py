import logging
from collections.abc import Callable, Collection

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.error import BoltError
from slack_sdk import WebClient

from speech_to_sheets.slack.allowlist import is_allowed
from speech_to_sheets.slack.errors import SlackError, slack_errors
from speech_to_sheets.slack.message import Message, parse_message

logger = logging.getLogger(__name__)

OnMessage = Callable[[Message, WebClient], None]


def build_app(
    bot_token: str,
    allowed_user_ids: Collection[str],
    on_message: OnMessage,
    verify_token: bool = True,
) -> App:
    """A Bolt app that passes each direct message from an allowed person to on_message.

    Bolt acknowledges each event at once and runs the listener on a worker thread, so a
    slow transcription never makes Slack resend the event. verify_token checks the bot
    token with Slack right away (tests turn it off: it needs the network).
    """
    try:
        with slack_errors("checking SLACK_BOT_TOKEN"):
            app = App(token=bot_token, token_verification_enabled=verify_token)
    except BoltError:  # Bolt's own error for a token Slack rejects
        raise SlackError(
            "checking SLACK_BOT_TOKEN: Slack rejected it; copy the Bot User OAuth Token again"
        ) from None

    allowed = frozenset(allowed_user_ids)

    @app.event("message")
    def _message(event: dict, client: WebClient) -> None:
        handle_event(event, client, allowed, on_message)

    return app


def handle_event(
    event: dict, client: WebClient, allowed_user_ids: Collection[str], on_message: OnMessage
) -> None:
    """Only direct messages someone sent: no channels, edits, deletions or bot messages."""
    if event.get("channel_type") != "im":
        return
    message = parse_message(event, event.get("channel", ""))
    if message is None or message.from_bot:
        return
    if not is_allowed(message, allowed_user_ids):
        logger.warning("Ignored a direct message from Slack user %s", message.user or "unknown")
        return
    on_message(message, client)


def run(app: App, app_token: str) -> None:
    """Connect with Socket Mode (no public URL or open port) and handle events until stopped."""
    with slack_errors("connecting with SLACK_APP_TOKEN"):
        SocketModeHandler(app, app_token).start()
