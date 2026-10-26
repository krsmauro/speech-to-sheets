from pathlib import Path

import yaml

HEADER = (
    "# Created by speech-to-sheets init. Not secret, but personal: keep it out of git.\n"
    "# Every other option, with its default, is in config.example.yaml.\n\n"
)


def write_config(path: Path, data: dict, overwrite: bool = False) -> None:
    """Write config.yaml. Refuses to replace an existing file unless `overwrite` is set."""
    if "secrets" in data:
        raise ValueError("secrets belong in .env, never in the config file")
    text = HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    with path.open("w" if overwrite else "x", encoding="utf-8") as file:
        file.write(text)
