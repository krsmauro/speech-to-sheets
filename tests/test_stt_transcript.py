import pytest

from speech_to_sheets.stt.transcript import clean_transcript


@pytest.mark.parametrize(
    "raw",
    ["", "   \n ", "[BLANK_AUDIO]", " (music) ", "*silence*", "...", "[Music] ¿? (applause)"],
)
def test_nothing_said_is_none(raw: str) -> None:
    assert clean_transcript(raw) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  forty   dollars\n for gas ", "forty dollars for gas"),
        ("20", "20"),
        ("[Music] twelve fifty at the bakery", "[Music] twelve fifty at the bakery"),
        ("café", "café"),
    ],
)
def test_speech_is_kept_with_whitespace_collapsed(raw: str, expected: str) -> None:
    assert clean_transcript(raw) == expected
