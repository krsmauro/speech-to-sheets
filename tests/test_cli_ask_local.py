from pathlib import Path

import pytest

from speech_to_sheets.cli.ask_local import (
    DEFAULT_MODEL,
    ask_language,
    ask_model_path,
    ask_slack_users,
    ask_timezone,
    local_timezone,
)
from tests.scripted import Script


def no_link(path: str) -> str:
    raise OSError("no such file")


@pytest.mark.parametrize(
    ("environ", "link", "expected"),
    [
        ({"TZ": "Europe/Madrid"}, no_link, "Europe/Madrid"),
        ({"TZ": ":America/Panama"}, no_link, "America/Panama"),
        ({}, lambda p: "/var/db/timezone/zoneinfo/Asia/Tokyo", "Asia/Tokyo"),
        ({}, lambda p: "../usr/share/zoneinfo/Europe/Lisbon", "Europe/Lisbon"),
        ({}, no_link, "UTC"),
        ({}, lambda p: "/somewhere/else", "UTC"),
        ({"TZ": "Not/AZone"}, no_link, "UTC"),
    ],
)
def test_local_timezone(environ: dict, link: object, expected: str) -> None:
    assert local_timezone(environ, link) == expected


def test_ask_timezone_rejects_names_it_does_not_know() -> None:
    script = Script("Mars/Olympus", "America/New_York")
    assert ask_timezone(script.prompter) == "America/New_York"
    assert script.said == [
        "Unknown timezone. Use an IANA name like America/New_York or Europe/Madrid."
    ]


def test_the_member_ids_can_be_left_blank() -> None:
    assert ask_slack_users(Script(" , ").prompter) == []


def test_several_member_ids_are_split_trimmed_and_deduplicated() -> None:
    script = Script("U0123ABCD, W0456EFGH ,U0123ABCD")
    assert ask_slack_users(script.prompter) == ["U0123ABCD", "W0456EFGH"]


def test_each_member_id_is_checked() -> None:
    script = Script("U0123ABCD, bob", "U0123ABCD")
    assert ask_slack_users(script.prompter) == ["U0123ABCD"]
    assert "Each member ID starts with U or W" in script.output


def test_model_path_defaults_and_warns_when_the_file_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    script = Script("")
    assert ask_model_path(script.prompter) == DEFAULT_MODEL
    assert "does not exist yet" in script.output


def test_model_path_that_exists_gets_no_warning(tmp_path: Path) -> None:
    model = tmp_path / "model.bin"
    model.write_bytes(b"")
    script = Script(str(model))
    assert ask_model_path(script.prompter) == str(model)
    assert script.said == []


def test_language_defaults_to_auto() -> None:
    assert ask_language(Script("").prompter) == "auto"
    assert ask_language(Script("es").prompter) == "es"
