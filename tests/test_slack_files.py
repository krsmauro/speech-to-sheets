from typing import Self

import pytest
import requests

from speech_to_sheets.slack import files
from speech_to_sheets.slack.errors import SlackError
from speech_to_sheets.slack.files import download

URL = "https://files.slack.com/files-pri/T1-F1/download/note.m4a"


class FakeResponse:
    def __init__(self, chunks: list[bytes], status: int = 200, content_type: str = "audio/mp4"):
        self.chunks = chunks
        self.status_code = status
        self.headers = {"Content-Type": content_type}

    def iter_content(self, chunk_size: int) -> list[bytes]:
        return self.chunks

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        pass


class FakeSession:
    def __init__(self, response: FakeResponse | Exception) -> None:
        self.response = response
        self.calls: list = []

    def get(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append((url, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_downloads_with_the_bot_token() -> None:
    session = FakeSession(FakeResponse([b"ab", b"cd"]))
    assert download(URL, "xoxb-1", session) == b"abcd"
    [(url, kwargs)] = session.calls
    assert url == URL and kwargs["headers"] == {"Authorization": "Bearer xoxb-1"}
    assert kwargs["stream"] is True and kwargs["timeout"] == 30


@pytest.mark.parametrize(
    "url",
    [
        "http://files.slack.com/x",
        "https://evil.example/x",
        "https://slack.com.evil.example/x",
        "https://evilslack.com/x",
        "",
    ],
)
def test_the_token_is_never_sent_outside_slack(url: str) -> None:
    session = FakeSession(FakeResponse([b"x"]))
    with pytest.raises(SlackError, match="refusing to send the bot token"):
        download(url, "xoxb-1", session)
    assert session.calls == []


def test_a_login_page_means_the_files_scope_is_missing() -> None:
    session = FakeSession(FakeResponse([b"<html>"], content_type="text/html; charset=utf-8"))
    with pytest.raises(SlackError, match="files:read"):
        download(URL, "xoxb-1", session)


def test_an_http_error_names_the_status() -> None:
    with pytest.raises(SlackError, match="HTTP 404"):
        download(URL, "xoxb-1", FakeSession(FakeResponse([], status=404)))


def test_a_network_error() -> None:
    with pytest.raises(SlackError, match="could not reach Slack"):
        download(URL, "xoxb-1", FakeSession(requests.ConnectionError("down")))


def test_a_huge_file_is_not_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(files, "MAX_DOWNLOAD_BYTES", 3)
    with pytest.raises(SlackError, match="larger than"):
        download(URL, "xoxb-1", FakeSession(FakeResponse([b"ab", b"cd"])))
