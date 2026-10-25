from dataclasses import dataclass
from typing import Literal

SUPPORTED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/gif", "image/webp"})


@dataclass(frozen=True)
class Image:
    """A photo for Claude, such as a receipt. The API accepts only these four formats."""

    media_type: str
    data: bytes

    def __post_init__(self) -> None:
        if self.media_type not in SUPPORTED_IMAGE_TYPES:
            raise ValueError(
                f"unsupported image type {self.media_type}; use JPEG, PNG, GIF or WebP"
            )


@dataclass(frozen=True)
class Turn:
    """One message of the Slack thread. `voice` marks a transcript, which may contain errors."""

    author: Literal["user", "bot"]
    text: str
    voice: bool = False


@dataclass(frozen=True)
class ExampleRow:
    """A recent sheet row as displayed, shown to Claude as a naming and category example."""

    date: str
    amount: str
    category: str
    description: str


@dataclass(frozen=True)
class ExtractionInput:
    """Everything the user sent about one expense: the thread, oldest first, and any photos."""

    turns: tuple[Turn, ...] = ()
    images: tuple[Image, ...] = ()
