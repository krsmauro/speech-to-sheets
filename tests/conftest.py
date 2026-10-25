from collections.abc import Callable
from pathlib import Path

import pytest
import yaml


def valid_yaml(model_path: str = "/models/ggml-test.bin") -> dict:
    """Smallest config.yaml that loads: only the keys that have no default."""
    return {
        "slack": {"allowed_user_id": "U0123ABC"},
        "sheets": {"sheet_id": "sheet-123", "tab": "Expenses"},
        "stt": {"model_path": model_path},
    }


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    """Valid secret environment variables with a real (empty) Google key file."""
    key = tmp_path / "google-key.json"
    key.write_text("{}")
    return {
        "SLACK_BOT_TOKEN": "xoxb-test-bot",
        "SLACK_APP_TOKEN": "xapp-test-app",
        "ANTHROPIC_API_KEY": "sk-test-anthropic",
        "GOOGLE_SERVICE_ACCOUNT_FILE": str(key),
    }


@pytest.fixture
def write_config(tmp_path: Path) -> Callable[[dict | str], Path]:
    def write(content: dict | str) -> Path:
        path = tmp_path / "config.yaml"
        path.write_text(content if isinstance(content, str) else yaml.safe_dump(content))
        return path

    return write
