from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from speech_to_sheets.config.columns import Columns


class Section(BaseModel):
    """Base for config.yaml sections: unknown keys are errors, so typos do not pass silently."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SlackConfig(Section):
    allowed_user_id: str = Field(pattern=r"^[UW][A-Z0-9]+$")


class SheetsConfig(Section):
    sheet_id: str = Field(min_length=1)
    tab: str = Field(min_length=1)
    columns: Columns = Field(default_factory=Columns)
    fallback_categories: list[str] = Field(default_factory=list)

    @field_validator("fallback_categories")
    @classmethod
    def _no_blank_categories(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if not all(cleaned):
            raise ValueError("categories must not be blank")
        return cleaned


class SttConfig(Section):
    whisper_cli: str = Field("whisper-cli", min_length=1)
    ffmpeg: str = Field("ffmpeg", min_length=1)
    model_path: Path
    language: str = Field("auto", min_length=1)
    timeout_seconds: int = Field(120, ge=1)

    @field_validator("model_path", mode="before")
    @classmethod
    def _expand_model_path(cls, value: object) -> object:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("set the path of a whisper.cpp ggml model file")
        return Path(value.strip()).expanduser()


class ExtractConfig(Section):
    model: str = Field("claude-haiku-5-5", min_length=1)
    example_rows: int = Field(30, ge=0)


class DedupeConfig(Section):
    retention_days: int = Field(30, ge=1)
    path: Path = Path("dedupe.sqlite")
