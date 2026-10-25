import anthropic


class ExtractError(Exception):
    """Extraction failed. The message is safe to show to the user."""


def describe_api_error(error: anthropic.APIError) -> str:
    """Most specific first, so each failure says what to do about it."""
    if isinstance(error, anthropic.AuthenticationError):
        return "Anthropic rejected the API key; check ANTHROPIC_API_KEY"
    if isinstance(error, anthropic.NotFoundError):
        return "Anthropic does not know this model; check extract.model"
    if isinstance(error, anthropic.RateLimitError):
        return "Anthropic rate limit reached; try again in a minute"
    if isinstance(error, anthropic.APIStatusError):
        return f"Anthropic API error {error.status_code}: {_api_message(error)}"
    if isinstance(error, anthropic.APIConnectionError):
        return "could not reach the Anthropic API (network problem or timeout)"
    return f"Anthropic API error: {error}"


def _api_message(error: anthropic.APIStatusError) -> str:
    """The API's own sentence (for example a low credit balance), not the SDK's raw dump."""
    body = error.body
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        return str(body["error"].get("message") or error.message)
    return error.message
