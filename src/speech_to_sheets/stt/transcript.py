import re

# Tags whisper emits instead of words, like [BLANK_AUDIO], (music) or *silence*.
_NON_SPEECH_TAG = re.compile(r"\[[^\]]*\]|\([^)]*\)|\*[^*]*\*")


def clean_transcript(raw: str) -> str | None:
    """Collapse whitespace. Return None when nothing was said: empty, punctuation or tags only."""
    text = " ".join(raw.split())
    spoken = _NON_SPEECH_TAG.sub("", text)
    if not any(char.isalnum() for char in spoken):
        return None
    return text
