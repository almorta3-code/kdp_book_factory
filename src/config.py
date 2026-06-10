from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")
    model_text_planner: str = Field(default="gemini-3.5-flash", alias="MODEL_TEXT_PLANNER")
    model_text_fast: str = Field(default="gemini-3.5-flash", alias="MODEL_TEXT_FAST")
    model_image: str = Field(default="gemini-3.1-flash-image", alias="MODEL_IMAGE")
    outputs_dir: Path = PROJECT_ROOT / "outputs"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings so the app reads configuration once per session."""
    settings = Settings()
    settings.outputs_dir.mkdir(parents=True, exist_ok=True)
    return settings
