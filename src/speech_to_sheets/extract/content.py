import base64

from speech_to_sheets.extract.inputs import ExtractionInput, Image, Turn


def build_user_content(request: ExtractionInput) -> list[dict]:
    """The single user message: images first, then the conversation as one text block."""
    if not request.turns and not request.images:
        raise ValueError("nothing to extract from: no text, transcript or image")
    blocks = [_image_block(image) for image in request.images]
    blocks.append({"type": "text", "text": _conversation(request.turns)})
    return blocks


def _image_block(image: Image) -> dict:
    data = base64.standard_b64encode(image.data).decode("ascii")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": image.media_type, "data": data},
    }


def _conversation(turns: tuple[Turn, ...]) -> str:
    if not turns:
        return "The user sent only the attached image, with no text."
    return "\n".join(["Conversation, oldest first:", *(_label(t) + t.text for t in turns)])


def _label(turn: Turn) -> str:
    if turn.author == "bot":
        return "You: "
    return "User (voice note transcript): " if turn.voice else "User: "
