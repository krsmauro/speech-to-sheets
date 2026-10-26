import anthropic
import pytest

from speech_to_sheets.extract.check import check_model
from speech_to_sheets.extract.errors import ExtractError
from tests.fake_anthropic import FakeClient, status_error


def test_looks_up_the_configured_model_without_sending_a_message() -> None:
    client = FakeClient()
    check_model(client, "claude-haiku-5-5")
    assert client.looked_up == ["claude-haiku-5-5"]
    assert client.calls == []


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (status_error(anthropic.AuthenticationError, 401), "check ANTHROPIC_API_KEY"),
        (status_error(anthropic.NotFoundError, 404), "check extract.model"),
    ],
)
def test_a_rejected_key_or_unknown_model_stops_startup(error: Exception, message: str) -> None:
    with pytest.raises(ExtractError, match=message):
        check_model(FakeClient(error=error), "claude-nonexistent")
