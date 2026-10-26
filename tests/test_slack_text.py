import pytest

from speech_to_sheets.slack.text import escape, to_plain


@pytest.mark.parametrize(
    ("raw", "plain"),
    [
        ("<http://amazon.com|amazon.com> 25", "amazon.com 25"),
        ("paid <https://shop.example/x?a=1&amp;b=2>", "paid https://shop.example/x?a=1&b=2"),
        ("<mailto:a@b.co|a@b.co>", "a@b.co"),
        ("AT&amp;T bill 40", "AT&T bill 40"),
        ("5 &lt; 6 &gt; 4", "5 < 6 > 4"),
        ("&amp;lt; stays as typed", "&lt; stays as typed"),
        ("ask <@U123>", "ask @U123"),
        ("lunch 12", "lunch 12"),
    ],
)
def test_slack_markup_becomes_what_the_person_typed(raw: str, plain: str) -> None:
    assert to_plain(raw) == plain


@pytest.mark.parametrize("text", ["AT&T <none> 5 > 4", "&amp; typed literally", "plain"])
def test_escaped_text_reads_back_unchanged(text: str) -> None:
    assert to_plain(escape(text)) == text


def test_escape_covers_the_three_characters_slack_reads_as_markup() -> None:
    assert escape("a & b <c> d") == "a &amp; b &lt;c&gt; d"
