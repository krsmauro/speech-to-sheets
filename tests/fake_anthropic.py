import json
from types import SimpleNamespace

import anthropic
import httpx2


class FakeClient:
    """Stands in for anthropic.Anthropic. messages.create records each call and answers with
    the given responses in order, the last one repeating; an exception in the list is
    raised instead. models.retrieve records the model looked up."""

    def __init__(self, *responses: object, error: Exception | None = None) -> None:
        self.calls: list[dict] = []
        self.looked_up: list[str] = []
        self.messages = self
        self.models = SimpleNamespace(retrieve=self._retrieve)
        self._responses = [error] if error is not None else list(responses)

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if not self._responses:
            return None
        answer = self._responses.pop(0) if len(self._responses) > 1 else self._responses[0]
        if isinstance(answer, Exception):
            raise answer
        return answer

    def _retrieve(self, model: str) -> object:
        self.looked_up.append(model)
        if self._responses and isinstance(self._responses[0], Exception):
            raise self._responses[0]
        return SimpleNamespace(id=model)


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
    keys = ("status", "amount", "category", "description", "date", "question")
    return {key: fields.get(key) for key in keys}


def status_error(cls: type, code: int, body: object = None) -> anthropic.APIStatusError:
    """An API error the way the SDK raises it, for example status_error(NotFoundError, 404)."""
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("server said no", response=httpx2.Response(code, request=request), body=body)
