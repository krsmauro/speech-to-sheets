from pathlib import Path

import pytest
import yaml

from speech_to_sheets.cli.write_config import write_config

DATA = {"timezone": "Europe/Madrid", "sheets": {"tab": "Expenses", "fallback_categories": ["Café"]}}


def test_writes_readable_yaml_in_the_given_order(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    write_config(path, DATA)
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# Created by speech-to-sheets init.")
    assert "Café" in text  # not escaped as \xE9
    assert text.index("timezone:") < text.index("sheets:")
    assert yaml.safe_load(text) == DATA


def test_never_replaces_an_existing_file_by_default(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("old: true\n")
    with pytest.raises(FileExistsError):
        write_config(path, DATA)
    assert path.read_text() == "old: true\n"


def test_replaces_when_asked(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("old: true\n")
    write_config(path, DATA, overwrite=True)
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == DATA


def test_refuses_secrets(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="secrets belong in .env"):
        write_config(tmp_path / "config.yaml", {"secrets": {"ANTHROPIC_API_KEY": "x"}})
    assert not (tmp_path / "config.yaml").exists()
