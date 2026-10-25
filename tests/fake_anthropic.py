import json
from types import SimpleNamespace


class FakeClient:
    """Stands in for anthropic.Anthropic: records each messages.create call."""

    def __init__(self, response: object = None, error: Exception | None = None) -> None:
        self.calls: list[dict] = []
        self.messages = self
        self._response = response
        self._error = error

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._response


def reply(payload: dict | str, stop_reason: str = "end_turn") -> SimpleNamespace:
    """A response shaped like Haiku 5.5's: a thinking block (empty text) before the answer."""
    text = payload if isinstance(payload, str) else json.dumps(payload)
    blocks = [
        SimpleNamespace(type="thinking", thinking=""),
        SimpleNamespace(type="text", text=text),
    ]
    return SimpleNamespace(stop_reason=stop_reason, content=blocks)


def answer(**fields: object) -> dict:
    """A schema-shaped answer with every field null unless given."""
    keys = ("status", "amount", "category", "description", "question")
    return {key: fields.get(key) for key in keys}
