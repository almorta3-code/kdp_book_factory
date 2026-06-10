from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from src.config import get_settings


T = TypeVar("T", bound=BaseModel)


def get_google_client() -> genai.Client:
    """Create a Google GenAI client from the loaded API key."""
    settings = get_settings()

    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is required to call the Gemini API.")

    return genai.Client(api_key=settings.google_api_key)


def generate_text(model: str, system_prompt: str, user_prompt: str) -> str:
    """Generate plain text with Gemini."""
    response = get_google_client().models.generate_content(
        model=model,
        contents=f"{system_prompt}\n\n{user_prompt}",
    )
    if not response.text:
        raise RuntimeError("Gemini returned no text.")
    return response.text


def generate_structured(model: str, system_prompt: str, user_prompt: str, schema: type[T]) -> T:
    """Generate JSON with Gemini and validate it against a Pydantic model."""
    response = get_google_client().models.generate_content(
        model=model,
        contents=f"{system_prompt}\n\n{user_prompt}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=schema.model_json_schema(),
        ),
    )
    if not response.text:
        raise RuntimeError(f"Gemini returned no parsed {schema.__name__} JSON.")
    return schema.model_validate_json(response.text)


def generate_image_file(model: str, prompt: str, output_path: str | Path) -> Path:
    """Generate one image with Gemini and save it as PNG."""
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    response = get_google_client().models.generate_content(
        model=model,
        contents=[prompt],
        config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
    )
    for part in response.parts or []:
        image = part.as_image()
        if image is not None:
            image.save(target_path, format="PNG")
            return target_path

    raise RuntimeError("Gemini image response did not include image data.")
