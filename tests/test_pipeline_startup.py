from collections.abc import Callable
from pathlib import Path

import pytest

from speech_to_sheets.config.settings import Settings, load_settings
from speech_to_sheets.dedupe.store import DedupeStore
from speech_to_sheets.pipeline import startup
from speech_to_sheets.pipeline.sheet_context import SheetContext
from speech_to_sheets.sheets.schema import Layout
from speech_to_sheets.stt.errors import SttError
from tests.conftest import valid_yaml


@pytest.fixture
def settings(tmp_path: Path, write_config: Callable, env: dict) -> Settings:
    data = valid_yaml() | {"dedupe": {"path": str(tmp_path / "dedupe.sqlite")}}
    return load_settings(write_config(data), tmp_path / "no.env", env)


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch) -> list:
    """Every outside connection replaced by a step recorded here, in order."""
    steps: list = []
    context = SheetContext(Layout(1, 2, 3, 4), ["Food"], [])

    def record(name: str, result: object = None) -> Callable:
        return lambda *args, **named: steps.append((name, *args, *named.values())) or result

    monkeypatch.setattr(startup, "check_stt", record("stt"))
    monkeypatch.setattr(startup, "open_worksheet", record("sheet", "worksheet"))
    monkeypatch.setattr(startup, "read_context", record("context", context))
    monkeypatch.setattr(startup, "make_client", record("claude", "client"))
    monkeypatch.setattr(startup, "check_model", record("model"))
    return steps


def test_checks_everything_once_then_returns_the_services(settings: Settings, opened: list) -> None:
    services = startup.open_services(settings)
    assert [step[0] for step in opened] == ["stt", "sheet", "context", "claude", "model"]
    assert opened[1][2:] == ("sheet-123", "Expenses")
    assert opened[2][1:] == ("worksheet", settings.sheets, 0)
    assert opened[3] == ("claude", "sk-test-anthropic")
    assert opened[4] == ("model", "client", "claude-haiku-5-5")
    assert (services.worksheet, services.claude, services.timezone) == (
        "worksheet",
        "client",
        "UTC",
    )
    assert services.store.path == settings.dedupe.path


def test_old_dedupe_entries_are_pruned_at_startup(settings: Settings, opened: list) -> None:
    DedupeStore(settings.dedupe.path, clock=lambda: 0.0).claim("D1:old")  # claimed in 1970
    services = startup.open_services(settings)
    assert services.store.claim("D1:old"), "pruned, so it counts as new again"


def test_a_missing_tool_stops_startup_before_anything_is_opened(
    settings: Settings, opened: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    def not_ready(stt: object) -> None:
        raise SttError("Speech-to-text is not ready")

    monkeypatch.setattr(startup, "check_stt", not_ready)
    with pytest.raises(SttError):
        startup.open_services(settings)
    assert opened == []
    assert not settings.dedupe.path.exists()
