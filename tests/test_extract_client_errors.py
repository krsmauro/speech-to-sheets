from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from speech_to_sheets.extract.client import extract
from speech_to_sheets.extract.errors import ExtractError
from speech_to_sheets.extract.inputs import ExtractionInput, Turn
from tests.fake_anthropic import FakeClient, answer, reply

REQUEST = ExtractionInput(turns=(Turn("user", "lunch 20000"),))
URL = "https://api.anthropic.com/v1/messages"


def run(client: FakeClient) -> object:
    return extract(client, REQUEST, ["Food"], [], "claude-haiku-5-5")


def status_error(cls: type, code: int, body: object = None) -> anthropic.APIStatusError:
    response = httpx2.Response(code, request=httpx2.Request("POST", URL))
    return cls("server said no", response=response, body=body)


LOW_CREDIT = {"type": "error", "error": {"type": "invalid_request_error", "message": "Low credit"}}


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (reply("I can't help with that", stop_reason="refusal"), "declined"),
        (reply('{"status": "comp', stop_reason="max_tokens"), "cut off"),
        (reply("not json"), "expected format"),
        (reply(answer(status="complete", amount=1, category="Cars", description="x")), "format"),
        (SimpleNamespace(stop_reason="end_turn", content=[]), "no answer"),
    ],
)
def test_bad_responses_raise_a_readable_error(response: object, message: str) -> None:
    client = FakeClient(response)
    with pytest.raises(ExtractError, match=message):
        run(client)


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (status_error(anthropic.AuthenticationError, 401), "ANTHROPIC_API_KEY"),
        (status_error(anthropic.NotFoundError, 404), "extract.model"),
        (status_error(anthropic.RateLimitError, 429), "rate limit"),
        (status_error(anthropic.InternalServerError, 500), "error 500: server said no"),
        (status_error(anthropic.BadRequestError, 400, LOW_CREDIT), "error 400: Low credit$"),
        (anthropic.APIConnectionError(request=httpx2.Request("POST", URL)), "could not reach"),
    ],
)
def test_api_errors_say_what_to_do(error: Exception, message: str) -> None:
    client = FakeClient(error=error)
    with pytest.raises(ExtractError, match=message):
        run(client)
