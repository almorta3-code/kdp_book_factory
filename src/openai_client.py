from __future__ import annotations

from openai import OpenAI

from src.config import get_settings


def get_openai_client() -> OpenAI:
    """Create an OpenAI client from the loaded API key."""
    settings = get_settings()

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to call the OpenAI API.")

    return OpenAI(api_key=settings.openai_api_key)
