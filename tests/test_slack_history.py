from speech_to_sheets.slack.history import dm_channels, messages_since


class Pages:
    """Stands in for one paginated Slack method: returns the given pages in order."""

    def __init__(self, *pages: dict) -> None:
        self.pages = list(pages)
        self.requests: list[dict] = []

    def __call__(self, **request: object) -> dict:
        self.requests.append(request)
        return self.pages[len(self.requests) - 1]


class FakeClient:
    def __init__(self, listing: Pages | None = None, history: Pages | None = None) -> None:
        self.conversations_list = listing
        self.conversations_history = history
        self.threads: dict[str, list[dict]] = {}
        self.thread_reads: list[str] = []

    def conversations_replies(self, channel: str, ts: str, **paging: object) -> dict:
        self.thread_reads.append(ts)
        return {"messages": self.threads[ts]}


def msg(ts: str, **fields: object) -> dict:
    return {"user": "U1", "text": f"at {ts}", "ts": ts} | fields


def test_only_the_allowed_peoples_channels_across_pages() -> None:
    listing = Pages(
        {"channels": [{"id": "D1", "user": "U1"}], "response_metadata": {"next_cursor": "c2"}},
        {"channels": [{"id": "D9", "user": "U9"}, {"id": "D2", "user": "U2"}]},
    )
    assert dm_channels(FakeClient(listing), ["U1", "U2"]) == ["D1", "D2"]
    assert listing.requests[0] == {"cursor": None, "limit": 200, "types": "im"}
    assert listing.requests[1]["cursor"] == "c2"


def test_messages_after_since_oldest_first_with_new_thread_replies() -> None:
    history = Pages(
        {
            "messages": [
                msg("300.0"),
                msg("150.0", thread_ts="150.0", reply_count=2, latest_reply="250.0"),
                msg("120.0", thread_ts="120.0", reply_count=1, latest_reply="130.0"),
            ]
        }
    )
    client = FakeClient(history=history)
    client.threads["150.0"] = [
        msg("150.0", thread_ts="150.0"),
        msg("160.0", thread_ts="150.0", bot_id="B1"),
        msg("250.0", thread_ts="150.0"),
    ]
    found = messages_since(client, "D1", since=200.0, threads_since=100.0)
    assert [(m.ts, m.thread_ts) for m in found] == [("250.0", "150.0"), ("300.0", None)]
    assert history.requests[0]["oldest"] == "100.000000"
    assert client.thread_reads == ["150.0"], "the thread with no reply after since is not read"


def test_a_thread_without_the_time_of_its_last_reply_is_read_to_be_safe() -> None:
    client = FakeClient(history=Pages({"messages": [msg("150.0", reply_count=1)]}))
    client.threads["150.0"] = [msg("150.0"), msg("210.0", thread_ts="150.0")]
    found = messages_since(client, "D1", since=200.0, threads_since=0.0)
    assert [m.ts for m in found] == ["210.0"]
