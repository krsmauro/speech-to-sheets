import pytest

from speech_to_sheets.extract.inputs import Image
from speech_to_sheets.slack import images
from speech_to_sheets.slack.images import image_for_claude, sniff_image_type
from speech_to_sheets.slack.message import SlackFile

# Only the first bytes of each format: enough to recognise it, not a real picture.
JPEG = b"\xff\xd8\xff\xe0" + b"\0" * 10
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 10
HEIC = b"\0\0\0\x18ftypheic" + b"\0" * 10


def photo(mimetype: str = "image/jpeg", size: int = 1000, thumbs: tuple = ()) -> SlackFile:
    return SlackFile("receipt", mimetype, "", size, "https://files.slack.com/orig", thumbs)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (JPEG, "image/jpeg"),
        (PNG, "image/png"),
        (b"GIF89a...", "image/gif"),
        (b"RIFF\0\0\0\0WEBPVP8 ", "image/webp"),
        (HEIC, None),
        (b"<html>", None),
        (b"", None),
    ],
)
def test_sniff_image_type(data: bytes, expected: str | None) -> None:
    assert sniff_image_type(data) == expected


def test_a_small_jpeg_is_sent_as_it_is() -> None:
    fetched = []
    files = {"https://files.slack.com/orig": JPEG}
    result = image_for_claude(photo(thumbs=("t1024",)), lambda u: fetched.append(u) or files[u])
    assert result == Image("image/jpeg", JPEG)
    assert fetched == ["https://files.slack.com/orig"]


def test_a_heic_photo_falls_back_to_the_largest_thumbnail() -> None:
    fetched = []
    files = {"t1024": JPEG, "t360": PNG}
    file = photo("image/heic", thumbs=("t1024", "t360"))
    assert image_for_claude(file, lambda u: fetched.append(u) or files[u]) == Image(
        "image/jpeg", JPEG
    )
    assert fetched == ["t1024"]


def test_a_photo_over_five_megabytes_uses_a_thumbnail() -> None:
    file = photo(size=6 * 1024 * 1024, thumbs=("t1024",))
    assert image_for_claude(file, {"t1024": PNG}.get) == Image("image/png", PNG)


def test_a_thumbnail_that_is_not_an_accepted_image_is_skipped() -> None:
    file = photo("image/heic", thumbs=("t1024", "t720"))
    assert image_for_claude(file, {"t1024": HEIC, "t720": PNG}.get) == Image("image/png", PNG)


def test_a_mislabelled_or_oversized_download_is_not_used(monkeypatch: pytest.MonkeyPatch) -> None:
    assert image_for_claude(photo(), {"https://files.slack.com/orig": HEIC}.get) is None
    monkeypatch.setattr(images, "MAX_IMAGE_BYTES", 4)
    assert image_for_claude(photo(size=3), {"https://files.slack.com/orig": JPEG}.get) is None
