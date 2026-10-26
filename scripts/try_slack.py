"""Check the Slack app: connect with Socket Mode and answer each direct message from you, in
its thread, with what the bot received. Nothing is written to the sheet.

    uv run python scripts/try_slack.py    # stop with Ctrl-C

Needs the full config.yaml and .env, both Slack tokens included. For each file it reports
the type Slack gives and whether it works: a photo as an image Claude accepts, a voice note
as a transcript. The terminal shows only file types and sizes, never message text,
transcripts or file contents; those go only to your Slack thread.
"""

import logging
import sys

from speech_to_sheets.config.errors import ConfigError
from speech_to_sheets.config.settings import Settings, load_settings
from speech_to_sheets.slack.client import build_app, run
from speech_to_sheets.slack.errors import SlackError
from speech_to_sheets.slack.files import download
from speech_to_sheets.slack.images import image_for_claude
from speech_to_sheets.slack.message import Message, SlackFile
from speech_to_sheets.slack.replies import post_reply
from speech_to_sheets.slack.thread import read_thread
from speech_to_sheets.stt.errors import SttError
from speech_to_sheets.stt.voice_note import transcribe_voice_note

log = logging.getLogger("try_slack")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        settings = load_settings()
    except ConfigError as error:
        print(error)
        return 2
    token = settings.secrets.slack_bot_token.get_secret_value()

    def echo(message: Message, client: object) -> None:
        lines = [f"Received {len(message.text)} characters of text."]
        try:
            if message.thread_ts:
                thread = read_thread(client, message.channel, message.thread_root)
                bots = sum(m.from_bot for m in thread)
                lines.append(f"A reply: the thread has {len(thread)} messages, {bots} from me.")
            lines += [describe(file, token, settings) for file in message.files]
            post_reply(client, message.channel, message.thread_root, "\n".join(lines))
        except SlackError as error:
            log.error("%s", error)
            return
        log.info("Echoed a message with %d file(s)", len(message.files))

    try:
        app = build_app(token, settings.slack.allowed_user_ids, echo)
        print("Connecting. Then send the bot a direct message in Slack. Ctrl-C stops.")
        run(app, settings.secrets.slack_app_token.get_secret_value())
    except SlackError as error:
        print(error)
        return 1
    return 0


def describe(file: SlackFile, token: str, settings: Settings) -> str:
    head = (
        f"File: {file.mimetype or 'no type'}, subtype {file.subtype or 'none'},"
        f" {file.size} bytes, {len(file.thumbs)} thumbnails"
    )
    log.info("%s", head)
    try:
        if file.is_image:
            image = image_for_claude(file, lambda url: download(url, token))
            if image is None:
                return f"{head}: no version of it is an image Claude accepts"
            return f"{head}: usable as {image.media_type}, {len(image.data)} bytes"
        if file.is_voice:
            transcript = transcribe_voice_note(download(file.url, token), settings.stt)
            return f"{head}: transcript: {transcript or '(no speech found)'}"
    except (SlackError, SttError) as error:
        return f"{head}: failed: {error}"
    return f"{head}: ignored, not a photo or a voice note"


if __name__ == "__main__":
    sys.exit(main())
