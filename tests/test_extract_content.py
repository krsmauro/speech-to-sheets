import pytest

from speech_to_sheets.extract.content import build_user_content
from speech_to_sheets.extract.inputs import ExtractionInput, Image, Turn


def test_thread_is_labelled_by_author_and_source() -> None:
    turns = (
        Turn("user", "35000"),
        Turn("bot", "What was it for?"),
        Turn("user", "groceries", voice=True),
    )
    [block] = build_user_content(ExtractionInput(turns=turns))
    assert block["text"].splitlines() == [
        "Conversation, oldest first:",
        "User: 35000",
        "You: What was it for?",
        "User (voice note transcript): groceries",
    ]


def test_images_come_before_the_text() -> None:
    images = (Image("image/png", b"a"), Image("image/webp", b"b"))
    blocks = build_user_content(ExtractionInput(turns=(Turn("user", "receipts"),), images=images))
    assert [b["type"] for b in blocks] == ["image", "image", "text"]


def test_nothing_to_extract_is_an_error() -> None:
    with pytest.raises(ValueError, match="nothing to extract"):
        build_user_content(ExtractionInput())


def test_unsupported_image_type_is_rejected() -> None:
    with pytest.raises(ValueError, match="JPEG, PNG, GIF or WebP"):
        Image("image/heic", b"photo")
