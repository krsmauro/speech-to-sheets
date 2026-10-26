from urllib.parse import urlparse

import requests

from speech_to_sheets.slack.errors import SlackError, slack_errors

MAX_DOWNLOAD_BYTES = 25_000_000  # far above a voice note or a photo; stops a huge video
TIMEOUT_SECONDS = 30


def download(url: str, token: str, session: object = requests) -> bytes:
    """Download a Slack-hosted file with the bot token. The token goes only to Slack's own
    HTTPS hosts; requests drops it if a redirect leaves the host."""
    parts = urlparse(url)
    host = parts.hostname or ""
    if parts.scheme != "https" or not (host == "slack.com" or host.endswith(".slack.com")):
        raise SlackError(f"refusing to send the bot token to {host or 'a file without a URL'}")
    headers = {"Authorization": f"Bearer {token}"}
    with (
        slack_errors("downloading a file from Slack"),
        session.get(url, headers=headers, timeout=TIMEOUT_SECONDS, stream=True) as response,
    ):
        if response.status_code != 200:
            raise SlackError(f"Slack refused the file download (HTTP {response.status_code})")
        if response.headers.get("Content-Type", "").startswith("text/html"):
            # Slack answers with its login page when the token may not read files.
            raise SlackError(
                "Slack sent a login page instead of the file: give the app the files:read"
                " scope and reinstall it"
            )
        return _read_capped(response)


def _read_capped(response: object) -> bytes:
    data = bytearray()
    for chunk in response.iter_content(chunk_size=65536):
        data += chunk
        if len(data) > MAX_DOWNLOAD_BYTES:
            raise SlackError(f"file larger than {MAX_DOWNLOAD_BYTES // 1_000_000} MB, not read")
    return bytes(data)
