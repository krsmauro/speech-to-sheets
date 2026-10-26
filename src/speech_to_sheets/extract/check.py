import anthropic

from speech_to_sheets.extract.errors import ExtractError, describe_api_error


def check_model(client: anthropic.Anthropic, model: str) -> None:
    """Fail fast at startup when Anthropic rejects the key or does not know the model.

    A model lookup costs no tokens. It cannot see a low credit balance; the first message
    reports that.
    """
    try:
        client.models.retrieve(model)
    except anthropic.APIError as error:
        raise ExtractError(describe_api_error(error)) from None
