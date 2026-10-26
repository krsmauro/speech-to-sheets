from slack_sdk.errors import SlackApiError

# 2025-01-15 04:30 UTC, which is Tuesday 2025-01-14 23:30 in America/Panama.
LATE_EVENING = 1_736_915_400


class FakeDm:
    """A direct message channel with the bot, standing in for slack_sdk.WebClient. People
    send messages, the bot's replies land in threads, and conversations.replies returns a
    whole thread, as Slack does. Each new message is a minute after the previous one."""

    channel = "D1"
    owner = "U1"  # the person this direct message channel is with

    def __init__(self) -> None:
        self.messages: list[dict] = []
        self.failing_posts = False
        self._clock = float(LATE_EVENING)

    def send(
        self,
        text: str = "",
        files: tuple[dict, ...] = (),
        reply_to: dict | None = None,
        user: str = "U1",
        at: float | None = None,
    ) -> dict:
        """The event Slack sends for a new message from a person."""
        event = {"type": "message", "channel_type": "im", "channel": self.channel}
        event |= {"user": user, "text": text, "ts": self._ts(at), "files": list(files)}
        if reply_to:
            event["thread_ts"] = reply_to["ts"]
        self.messages.append(event)
        return event

    def conversations_replies(self, channel: str, ts: str, **paging: object) -> dict:
        thread = [m for m in self.messages if ts in (m["ts"], m.get("thread_ts"))]
        return {"messages": thread}

    def conversations_list(self, types: str, **paging: object) -> dict:
        return {"channels": [{"id": self.channel, "user": self.owner, "is_im": True}]}

    def conversations_history(self, channel: str, oldest: str, **paging: object) -> dict:
        """Top-level messages after oldest, newest first; a thread's first message carries
        its reply count and the time of its last reply, as Slack lists them."""
        listed = []
        for message in self.messages:
            if message.get("thread_ts", message["ts"]) != message["ts"]:
                continue  # a reply: Slack lists it only under its thread
            if float(message["ts"]) <= float(oldest):
                continue
            replies = [m["ts"] for m in self.messages if m.get("thread_ts") == message["ts"]]
            if replies:
                message = message | {"reply_count": len(replies), "latest_reply": max(replies)}
            listed.append(message)
        return {"messages": listed[::-1]}

    def chat_postMessage(self, channel: str, thread_ts: str, text: str) -> dict:
        if self.failing_posts:
            raise SlackApiError("failed", {"ok": False, "error": "ratelimited"})
        ts = self._ts(None)
        bot = {"bot_id": "B1", "user": "UBOT", "text": text, "ts": ts, "thread_ts": thread_ts}
        self.messages.append(bot)
        return {"ok": True, "ts": ts}

    def bot_texts(self) -> list[str]:
        return [m["text"] for m in self.messages if "bot_id" in m]

    def _ts(self, at: float | None) -> str:
        self._clock = at if at is not None else self._clock + 60
        return f"{self._clock:.6f}"
