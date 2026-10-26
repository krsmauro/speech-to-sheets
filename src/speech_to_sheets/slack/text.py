import re

# Slack wraps links, mentions and channel names in angle brackets, with an optional label:
# <http://amazon.com|amazon.com>, <mailto:a@b.co|a@b.co>, <@U123>.
_MARKUP = re.compile(r"<([^<>|]*)\|([^<>]*)>|<([^<>]*)>")


def to_plain(text: str) -> str:
    """A Slack message as the person typed it: links show their label, and the three
    characters Slack escapes (&, <, >) come back. Slack auto-links domains, so a typed
    amazon.com arrives as <http://amazon.com|amazon.com>."""
    text = _MARKUP.sub(lambda match: match.group(2) or match.group(3) or match.group(1), text)
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def escape(text: str) -> str:
    """Plain text ready to post: Slack reads &, < and > as markup, so they are escaped."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
