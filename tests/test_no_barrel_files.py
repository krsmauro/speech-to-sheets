from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_init_files_are_empty() -> None:
    init_files = [*(ROOT / "src").rglob("__init__.py"), *(ROOT / "tests").rglob("__init__.py")]
    assert init_files, "expected at least one package"
    not_empty = [str(p.relative_to(ROOT)) for p in init_files if p.read_text().strip()]
    assert not not_empty, f"Barrel files are not allowed, keep __init__.py empty: {not_empty}"
