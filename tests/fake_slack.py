from slack_sdk.errors import SlackApiError


class FakeSlack:
    """Stands in for slack_sdk.WebClient: thread pages to return and every reply posted."""

    def __init__(self, pages: list[dict] | None = None, error: str | None = None) -> None:
        self.pages = pages or []
        self.error = error
        self.reads: list[dict] = []
        self.posts: list[dict] = []

    def conversations_replies(self, **kwargs: object) -> dict:
        self.reads.append(kwargs)
        self._maybe_fail()
        return self.pages[len(self.reads) - 1]

    def chat_postMessage(self, **kwargs: object) -> dict:
        self.posts.append(kwargs)
        self._maybe_fail()
        return {"ok": True, "ts": f"9.{len(self.posts)}"}

    def _maybe_fail(self) -> None:
        if self.error:
            response = {"ok": False, "error": self.error, "needed": "chat:write"}
            raise SlackApiError("failed", response)
