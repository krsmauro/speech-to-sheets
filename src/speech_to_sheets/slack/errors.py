from collections.abc import Iterator
from contextlib import contextmanager

from slack_sdk.errors import SlackApiError

# What to do about the Slack error codes a setup mistake causes.
HINTS = {
    "invalid_auth": "the token was rejected; copy it again from the app settings",
    "not_authed": "no token was sent",
    "account_inactive": "the app was uninstalled or its token revoked; reinstall it",
    "ratelimited": "Slack asks to slow down; try again in a minute",
}


class SlackError(Exception):
    """A Slack step failed. The message is safe to show to the user and never holds a token."""


@contextmanager
def slack_errors(action: str, scope: str | None = None) -> Iterator[None]:
    """Turn Slack SDK and network errors into one SlackError that says what was being done.
    scope names the one scope the action needs, when Slack's own answer lists several."""
    try:
        yield
    except SlackApiError as error:
        raise SlackError(f"{action}: Slack API error {_describe(error.response, scope)}") from None
    except OSError:  # urllib errors from the SDK, requests errors and timeouts all land here
        raise SlackError(f"{action}: could not reach Slack (network or timeout)") from None


def _describe(response: object, scope: str | None) -> str:
    get = getattr(response, "get", None)
    code = (get("error") if get else None) or "unknown_error"
    if code == "missing_scope":
        needed = scope or get("needed") or "a scope"
        return f"{code}: add {needed} to the app's bot scopes, then reinstall the app"
    hint = HINTS.get(code)
    return f"{code}: {hint}" if hint else code
