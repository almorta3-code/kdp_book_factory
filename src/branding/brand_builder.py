from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.compliance.provenance_engine import record_prompt
from src.config import get_settings
from src.google_client import generate_structured


BRANDS_DIR = Path(__file__).resolve().parents[2] / "projects" / "brands"


class BrandProfile(BaseModel):
    """Reusable publishing brand profile for a workbook series."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    brand_name: str = Field(..., min_length=3, max_length=80)
    slogan: str = Field(..., min_length=3, max_length=140)
    visual_identity: str = Field(..., min_length=20, max_length=1000)
    color_palette: list[str] = Field(..., min_length=3, max_length=8)
    mascot_concept: str = Field(..., min_length=10, max_length=800)
    publishing_strategy: str = Field(..., min_length=20, max_length=1500)
    future_series: list[str] = Field(..., min_length=3, max_length=20)

    @field_validator("brand_name", "slogan", "visual_identity", "mascot_concept", "publishing_strategy")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Brand text fields cannot be blank.")
        return cleaned

    @field_validator("color_palette", "future_series")
    @classmethod
    def strip_list_items(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("Brand lists cannot contain blank values.")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Brand lists must not contain duplicates.")
        return cleaned


def _system_prompt() -> str:
    return """
You are a senior children's publishing brand strategist.

Create original, long-term publishing brands for educational activity workbooks.

Rules:
- Avoid copyrighted characters, trademarked styles, and brand names that are too close to existing famous brands.
- Make the brand expandable across KDP books, printables, classroom packs, bundles, and seasonal editions.
- The brand should feel trustworthy to parents and fun for children.
- Names should be simple, memorable, and broad enough for multiple series.
- Example tone: Little Explorer Club, Tiny Science Lab, Adventure Academy.
""".strip()


def _user_prompt(target_niche: str, age_range: str) -> str:
    return f"""
Create a BrandProfile for a children's activity workbook publishing brand.

Target niche: {target_niche}
Age range: {age_range}

Include a clear brand name, slogan, visual identity, color palette, mascot concept, publishing strategy, and future series ideas.
""".strip()


def build_brand_profile(target_niche: str, age_range: str) -> BrandProfile:
    """Generate a structured long-term publishing brand profile."""
    cleaned_niche = target_niche.strip()
    cleaned_age = age_range.strip()
    if len(cleaned_niche) < 3:
        raise ValueError("Enter a target niche with at least 3 characters.")
    if len(cleaned_age) < 2:
        raise ValueError("Enter an age range.")

    settings = get_settings()
    system_prompt = _system_prompt()
    user_prompt = _user_prompt(cleaned_niche, cleaned_age)
    parsed = generate_structured(settings.model_text_planner, system_prompt, user_prompt, BrandProfile)
    try:
        record_prompt("brand_builder", settings.model_text_planner, f"{system_prompt}\n\n{user_prompt}", f"Generated brand profile for {parsed.brand_name}")
    except Exception:
        pass
    return parsed


def _slugify(text: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "_" for character in text).strip("_")
    return slug or "publishing_brand"


def save_brand_profile(profile: BrandProfile, output_dir: Path | None = None) -> Path:
    """Save brand profiles under projects/brands."""
    target_dir = output_dir or BRANDS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_path = target_dir / f"{timestamp}_{_slugify(profile.brand_name)}.json"
    output_path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    return output_path
