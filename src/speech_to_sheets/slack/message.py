from dataclasses import dataclass, field

# Message subtypes that are something someone sent. Edits, deletions, joins and the like
# are not, and are ignored. A message with files has no subtype or the old file_share one;
# bot_message keeps the bot's own questions when a thread is re-read.
SENT_SUBTYPES = (None, "file_share", "thread_broadcast", "bot_message")
THUMB_KEYS = ("thumb_1024", "thumb_960", "thumb_720", "thumb_480", "thumb_360")


@dataclass(frozen=True)
class SlackFile:
    """The parts of a Slack file object the bot uses. URLs need the bot token to download."""

    name: str
    mimetype: str
    subtype: str
    size: int
    url: str
    thumbs: tuple[str, ...] = ()  # largest first

    @property
    def is_voice(self) -> bool:
        # How Slack labels recorded voice clips is not documented; any audio file counts.
        return self.subtype == "slack_audio" or self.mimetype.startswith("audio/")

    @property
    def is_image(self) -> bool:
        return self.mimetype.startswith("image/")


@dataclass(frozen=True)
class Message:
    channel: str
    ts: str
    user: str
    text: str
    from_bot: bool = False
    thread_ts: str | None = None
    files: tuple[SlackFile, ...] = field(default_factory=tuple)

    @property
    def message_id(self) -> str:
        """Unique per workspace: ts is unique within a channel. The dedupe store key."""
        return f"{self.channel}:{self.ts}"

    @property
    def thread_root(self) -> str:
        """The ts of the thread's first message; replies to this message go there."""
        return self.thread_ts or self.ts


def parse_message(raw: dict, channel: str) -> Message | None:
    """A message event or a conversations.replies entry, or None if the user did not send it."""
    if raw.get("subtype") not in SENT_SUBTYPES or not raw.get("ts"):
        return None
    return Message(
        channel=channel,
        ts=raw["ts"],
        user=raw.get("user", ""),
        text=raw.get("text", ""),
        from_bot="bot_id" in raw,
        thread_ts=raw.get("thread_ts"),
        files=tuple(_file(item) for item in raw.get("files", []) if not item.get("is_external")),
    )


def _file(raw: dict) -> SlackFile:
    return SlackFile(
        name=raw.get("name", ""),
        mimetype=raw.get("mimetype", ""),
        subtype=raw.get("subtype", ""),
        size=int(raw.get("size") or 0),
        url=raw.get("url_private_download") or raw.get("url_private", ""),
        thumbs=tuple(raw[key] for key in THUMB_KEYS if raw.get(key)),
    )
