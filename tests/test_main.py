from pathlib import Path

import pytest

from speech_to_sheets import main as entry


def test_init_passes_the_file_options(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr(entry, "run_init", lambda *args: calls.append(args[:2]) or 0)
    assert entry.main(["init", "--config", "other.yaml", "--env", "secrets.env"]) == 0
    assert entry.main(["init"]) == 0
    assert calls == [
        (Path("other.yaml"), Path("secrets.env")),
        (Path("config.yaml"), Path(".env")),
    ]


@pytest.mark.parametrize("stop", [KeyboardInterrupt, EOFError])
def test_stopping_at_a_question_writes_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, stop: type
) -> None:
    def interrupted(*args: object) -> int:
        raise stop

    monkeypatch.setattr(entry, "run_init", interrupted)
    assert entry.main(["init"]) == 130
    assert "Cancelled. Nothing written." in capsys.readouterr().out


def test_a_command_is_required() -> None:
    with pytest.raises(SystemExit) as caught:
        entry.main([])
    assert caught.value.code == 2


def test_run_passes_the_file_options(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr(entry, "run_bot", lambda *args: calls.append(args) or 0)
    assert entry.main(["run", "--config", "other.yaml", "--env", "secrets.env"]) == 0
    assert entry.main(["run"]) == 0
    assert calls == [
        (Path("other.yaml"), Path("secrets.env")),
        (Path("config.yaml"), Path(".env")),
    ]
