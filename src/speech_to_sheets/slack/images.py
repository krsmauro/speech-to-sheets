from collections.abc import Callable

from speech_to_sheets.extract.inputs import SUPPORTED_IMAGE_TYPES, Image
from speech_to_sheets.slack.message import SlackFile

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # the Anthropic API's limit per image


def image_for_claude(file: SlackFile, fetch: Callable[[str], bytes]) -> Image | None:
    """The photo in a form the API accepts: the original when it is JPEG, PNG, GIF or WebP
    and at most 5 MB, otherwise Slack's largest thumbnail (an iPhone HEIC photo, for
    example). The type is read from the bytes, not trusted from Slack. None if nothing fits."""
    urls = list(file.thumbs)
    if file.mimetype in SUPPORTED_IMAGE_TYPES and 0 < file.size <= MAX_IMAGE_BYTES:
        urls.insert(0, file.url)
    for url in urls:
        data = fetch(url)
        media_type = sniff_image_type(data)
        if media_type and len(data) <= MAX_IMAGE_BYTES:
            return Image(media_type, data)
    return None


def sniff_image_type(data: bytes) -> str | None:
    """The media type from the file's first bytes, for the four types the API accepts."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None
