from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_to_sheets.cli import run as command
from speech_to_sheets.config.settings import load_settings
from speech_to_sheets.sheets.errors import SheetsError
from speech_to_sheets.slack.errors import SlackError
from tests.conftest import valid_yaml


@pytest.fixture
def started(
    monkeypatch: pytest.MonkeyPatch, write_config: Callable, env: dict, tmp_path: Path
) -> dict:
    """Valid settings, with the services, the Slack app and the connection faked."""
    seen: dict = {"config": write_config(valid_yaml()), "env": tmp_path / ".env"}
    monkeypatch.setattr(
        command, "load_settings", lambda config, env_file: load_settings(config, env_file, env)
    )
    monkeypatch.setattr(command, "open_services", lambda settings: "services")

    def build_app(token: str, allowed: list, on_message: Callable) -> SimpleNamespace:
        seen.update(token=token, allowed=allowed, on_message=on_message)
        return SimpleNamespace(client="client")

    def start_catch_up(*args: object) -> None:
        seen["catch_up"] = args

    monkeypatch.setattr(command, "build_app", build_app)
    monkeypatch.setattr(command, "start_catch_up", start_catch_up)
    monkeypatch.setattr(command, "run", lambda app, token: seen.update(app=app, app_token=token))
    return seen


def test_each_message_goes_to_the_pipeline_with_the_opened_services(
    started: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    handled = []
    monkeypatch.setattr(command, "handle_message", lambda *args: handled.append(args))
    assert command.run_bot(started["config"], started["env"]) == 0
    assert (started["token"], started["allowed"]) == ("xoxb-test-bot", ["U0123ABC"])
    assert (started["app"].client, started["app_token"]) == ("client", "xapp-test-app")
    assert started["catch_up"] == ("client", "services", ["U0123ABC"], 30)
    started["on_message"]("message", "client")
    assert handled == [("message", "client", "services")]


def test_a_setup_problem_stops_startup_with_its_message(
    started: dict, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    def no_tab(settings: object) -> None:
        raise SheetsError("sheets.tab: no tab named Gastos; tabs found: Expenses")

    monkeypatch.setattr(command, "open_services", no_tab)
    assert command.run_bot(started["config"], started["env"]) == 1
    assert "Not started: sheets.tab: no tab named Gastos" in capsys.readouterr().err
    assert "app" not in started, "never connected"


def test_a_missing_config_file_is_a_clear_message(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    assert command.run_bot(tmp_path / "config.yaml", tmp_path / ".env") == 1
    assert "config.yaml not found" in capsys.readouterr().err


def test_ctrl_c_stops_cleanly(
    started: dict, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    def interrupted(app: object, token: str) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(command, "run", interrupted)
    assert command.run_bot(started["config"], started["env"]) == 0
    assert "Stopped." in capsys.readouterr().err


def test_a_missing_slack_scope_stops_startup_before_connecting(
    started: dict, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    def no_scope(*args: object) -> None:
        raise SlackError("listing the bot's direct messages: missing_scope: add im:read")

    monkeypatch.setattr(command, "start_catch_up", no_scope)
    assert command.run_bot(started["config"], started["env"]) == 1
    assert "Not started: listing the bot's direct messages" in capsys.readouterr().err
    assert "app_token" not in started, "never connected"
