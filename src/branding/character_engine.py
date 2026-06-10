from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.branding.brand_builder import BRANDS_DIR
from src.compliance.provenance_engine import record_prompt
from src.config import get_settings
from src.google_client import generate_structured


class CharacterProfile(BaseModel):
    """Reusable mascot character profile for long-running publishing brands."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    name: str = Field(..., min_length=2, max_length=80)
    species: str = Field(..., min_length=2, max_length=80)
    age_appearance: str = Field(..., min_length=3, max_length=120)
    personality: str = Field(..., min_length=10, max_length=600)
    visual_traits: str = Field(..., min_length=10, max_length=800)
    clothing: str = Field(..., min_length=3, max_length=500)
    accessories: str = Field(..., min_length=3, max_length=500)
    prompt_template: str = Field(..., min_length=30, max_length=1500)
    front_pose_prompt: str = Field(..., min_length=30, max_length=1500)
    side_pose_prompt: str = Field(..., min_length=30, max_length=1500)
    happy_prompt: str = Field(..., min_length=30, max_length=1500)
    sad_prompt: str = Field(..., min_length=30, max_length=1500)
    excited_prompt: str = Field(..., min_length=30, max_length=1500)
    teaching_prompt: str = Field(..., min_length=30, max_length=1500)

    @field_validator(
        "name",
        "species",
        "age_appearance",
        "personality",
        "visual_traits",
        "clothing",
        "accessories",
        "prompt_template",
        "front_pose_prompt",
        "side_pose_prompt",
        "happy_prompt",
        "sad_prompt",
        "excited_prompt",
        "teaching_prompt",
    )
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Character fields cannot be blank.")
        return cleaned


def _system_prompt() -> str:
    return """
You are a senior children's publishing character designer.

Create reusable mascot characters that can remain consistent across 100 children's activity books.

Rules:
- Avoid copyrighted characters, trademarked worlds, and recognizable branded styles.
- Keep the mascot original, simple, friendly, and easy to redraw.
- Make visual traits specific and repeatable: shape language, colors, face, markings, clothing, and accessories.
- Do not put readable text inside image prompts.
- Prompt templates must preserve character consistency across poses, emotions, and teaching scenes.
""".strip()


def _user_prompt(target_niche: str, brand_name: str, audience: str) -> str:
    return f"""
Create a CharacterProfile for a reusable mascot.

Target niche: {target_niche}
Brand name: {brand_name}
Audience: {audience}

Generate one consistent mascot character and include prompts for:
- front pose
- side pose
- happy expression
- sad expression
- excited expression
- teaching pose

Every prompt should include the same identity details from the prompt_template so the character can be reused across many books.
""".strip()


def build_character_profile(target_niche: str, brand_name: str, audience: str) -> CharacterProfile:
    """Generate a reusable mascot profile with consistent image prompts."""
    cleaned_niche = target_niche.strip()
    cleaned_brand = brand_name.strip()
    cleaned_audience = audience.strip()
    if len(cleaned_niche) < 3:
        raise ValueError("Enter a target niche.")
    if len(cleaned_brand) < 2:
        raise ValueError("Enter a brand name.")
    if len(cleaned_audience) < 3:
        raise ValueError("Enter an audience.")

    settings = get_settings()
    system_prompt = _system_prompt()
    user_prompt = _user_prompt(cleaned_niche, cleaned_brand, cleaned_audience)
    parsed = generate_structured(settings.model_text_planner, system_prompt, user_prompt, CharacterProfile)
    try:
        record_prompt("character_engine", settings.model_text_planner, f"{system_prompt}\n\n{user_prompt}", f"Generated character profile for {parsed.name}")
    except Exception:
        pass
    return parsed


def save_character_profile(profile: CharacterProfile, output_dir: Path | None = None) -> Path:
    """Save the reusable mascot profile as character_profile.json."""
    target_dir = output_dir or (BRANDS_DIR / "characters" / _slugify(profile.name))
    target_dir.mkdir(parents=True, exist_ok=True)

    output_path = target_dir / "character_profile.json"
    output_path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    return output_path


def _slugify(text: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "_" for character in text).strip("_")
    return slug or "character"
