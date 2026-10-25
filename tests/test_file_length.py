import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARD_LIMIT = 150
SOFT_LIMIT = 100


def _python_files() -> list[Path]:
    return sorted([*(ROOT / "src").rglob("*.py"), *(ROOT / "tests").rglob("*.py")])


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def test_no_file_exceeds_hard_limit() -> None:
    too_long = {p.relative_to(ROOT): _line_count(p) for p in _python_files()}
    too_long = {p: n for p, n in too_long.items() if n > HARD_LIMIT}
    assert not too_long, f"Files over {HARD_LIMIT} lines, split them: {too_long}"


def test_warn_about_files_over_soft_limit() -> None:
    for path in _python_files():
        count = _line_count(path)
        if count > SOFT_LIMIT:
            warnings.warn(f"{path.relative_to(ROOT)} has {count} lines (aim for < {SOFT_LIMIT})")
