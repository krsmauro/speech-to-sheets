from collections.abc import Callable, Iterator

from speech_to_sheets.slack.errors import slack_errors

PAGE_SIZE = 200  # Slack's recommended maximum per request


def pages(
    call: Callable[..., dict], action: str, scope: str | None = None, **arguments: object
) -> Iterator[dict]:
    """Every page of a paginated Slack Web API call, following next_cursor. A failed request
    raises SlackError naming the action (and the scope it needs, see slack_errors)."""
    cursor = None
    while True:
        with slack_errors(action, scope):
            response = call(cursor=cursor, limit=PAGE_SIZE, **arguments)
        yield response
        cursor = (response.get("response_metadata") or {}).get("next_cursor")
        if not cursor:
            return
