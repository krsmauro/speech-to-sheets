from datetime import UTC, datetime

import pytest

from speech_to_sheets.slack.message import Message, SlackFile, parse_message, sent_at

PHOTO = {
    "name": "IMG_1.HEIC",
    "mimetype": "image/heic",
    "size": 2_400_000,
    "url_private": "https://files.slack.com/files-pri/T1-F1/img_1.heic",
    "url_private_download": "https://files.slack.com/files-pri/T1-F1/download/img_1.heic",
    "thumb_360": "https://files.slack.com/t360.jpg",
    "thumb_1024": "https://files.slack.com/t1024.jpg",
}


def test_a_plain_direct_message() -> None:
    raw = {"type": "message", "user": "U1", "text": "lunch 12", "ts": "1700000000.000100"}
    message = parse_message(raw, "D1")
    assert message == Message(channel="D1", ts="1700000000.000100", user="U1", text="lunch 12")
    assert message.message_id == "D1:1700000000.000100"
    assert message.thread_root == "1700000000.000100"


def test_a_reply_in_a_thread_belongs_to_its_root() -> None:
    raw = {"user": "U1", "text": "the bakery", "ts": "2.0", "thread_ts": "1.0"}
    assert parse_message(raw, "D1").thread_root == "1.0"


def test_files_keep_the_download_url_and_the_largest_thumbnails_first() -> None:
    raw = {"user": "U1", "ts": "1.0", "files": [PHOTO]}
    [photo] = parse_message(raw, "D1").files
    assert photo == SlackFile(
        name="IMG_1.HEIC",
        mimetype="image/heic",
        subtype="",
        size=2_400_000,
        url=PHOTO["url_private_download"],
        thumbs=(PHOTO["thumb_1024"], PHOTO["thumb_360"]),
    )
    assert photo.is_image and not photo.is_voice


@pytest.mark.parametrize(
    ("mimetype", "subtype", "voice"),
    [
        ("audio/mp4", "", True),
        ("audio/webm", "slack_audio", True),
        ("video/mp4", "slack_audio", True),
        ("video/mp4", "", False),
        ("application/pdf", "", False),
    ],
)
def test_any_audio_counts_as_a_voice_note(mimetype: str, subtype: str, voice: bool) -> None:
    raw = {"user": "U1", "ts": "1.0", "files": [{"mimetype": mimetype, "subtype": subtype}]}
    assert parse_message(raw, "D1").files[0].is_voice is voice


def test_external_files_are_dropped_so_the_token_never_goes_there() -> None:
    raw = {"user": "U1", "ts": "1.0", "files": [{**PHOTO, "is_external": True}]}
    assert parse_message(raw, "D1").files == ()


@pytest.mark.parametrize("subtype", ["message_changed", "message_deleted", "channel_join"])
def test_edits_deletions_and_joins_are_ignored(subtype: str) -> None:
    assert parse_message({"subtype": subtype, "ts": "1.0"}, "D1") is None


def test_messages_with_files_and_bot_messages_are_kept() -> None:
    assert parse_message({"subtype": "file_share", "user": "U1", "ts": "1.0"}, "D1")
    bot = parse_message({"subtype": "bot_message", "bot_id": "B1", "ts": "1.0"}, "D1")
    assert bot.from_bot
    assert parse_message({"bot_id": "B1", "user": "U9", "ts": "1.0"}, "D1").from_bot


def test_text_arrives_as_plain_text() -> None:
    raw = {"user": "U1", "text": "<http://amazon.com|amazon.com> AT&amp;T", "ts": "1.0"}
    assert parse_message(raw, "D1").text == "amazon.com AT&T"


def test_sent_at_reads_the_ts_as_utc() -> None:
    assert sent_at("1736915400.000100") == datetime(2025, 1, 15, 4, 30, 0, 100, tzinfo=UTC)
