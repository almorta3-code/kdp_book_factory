from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


STYLES_DIR = Path(__file__).resolve().parents[2] / "projects" / "styles"


class IllustrationStyle(BaseModel):
    """Reusable prompt modifiers for one illustration style."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    style_name: str = Field(..., min_length=3, max_length=80)
    image_prompt_modifiers: str = Field(..., min_length=10, max_length=1000)
    cover_modifiers: str = Field(..., min_length=10, max_length=1000)
    coloring_page_modifiers: str = Field(..., min_length=10, max_length=1000)
    icon_modifiers: str = Field(..., min_length=10, max_length=1000)

    @field_validator(
        "style_name",
        "image_prompt_modifiers",
        "cover_modifiers",
        "coloring_page_modifiers",
        "icon_modifiers",
    )
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Style fields cannot be blank.")
        return cleaned


PRELOADED_STYLES: list[IllustrationStyle] = [
    IllustrationStyle(
        style_name="Cute Pastel",
        image_prompt_modifiers="Soft pastel colors, rounded shapes, gentle expressions, cozy kid-friendly educational workbook look.",
        cover_modifiers="Bright pastel cover composition, friendly main character, clean open space for title added later.",
        coloring_page_modifiers="Simple rounded black-and-white outlines, large open coloring spaces, no shading, no readable text.",
        icon_modifiers="Small soft pastel icon, rounded silhouette, simple recognizable shape, transparent background when possible.",
    ),
    IllustrationStyle(
        style_name="Montessori",
        image_prompt_modifiers="Calm realistic educational style, natural colors, simple uncluttered objects, hands-on learning feel.",
        cover_modifiers="Clean natural classroom-inspired cover, soft earth tones, tidy composition, open space for title.",
        coloring_page_modifiers="Clear realistic outlines, minimal background, object-centered learning page, no shading, no readable text.",
        icon_modifiers="Simple natural-material inspired icon, muted colors, clean shape, transparent background when possible.",
    ),
    IllustrationStyle(
        style_name="Cartoon Classroom",
        image_prompt_modifiers="Cheerful classroom cartoon style, expressive original characters, bright balanced colors, playful learning energy.",
        cover_modifiers="Fun classroom-themed cover scene, lively original mascot, school-friendly props, clean title space.",
        coloring_page_modifiers="Bold cartoon outlines, friendly expressions, simple props, large fill areas, no readable text.",
        icon_modifiers="Bright classroom icon, simple cartoon shape, friendly and readable at small size.",
    ),
    IllustrationStyle(
        style_name="Watercolor Educational",
        image_prompt_modifiers="Gentle watercolor texture, soft edges, educational nature-journal feel, warm and calm.",
        cover_modifiers="Soft watercolor cover illustration, airy composition, delicate educational details, open space for title.",
        coloring_page_modifiers="Clean line-art version of watercolor subject, no wash texture, no shading, large open areas.",
        icon_modifiers="Simple watercolor-style icon, soft color edges, minimal detail, transparent background when possible.",
    ),
    IllustrationStyle(
        style_name="Bold Coloring Book",
        image_prompt_modifiers="High-contrast bold line art, playful shapes, simple child-friendly composition, print-ready clarity.",
        cover_modifiers="Strong bold cover illustration, large readable visual shapes, high contrast, open space for text added later.",
        coloring_page_modifiers="Extra-thick black outlines, no shading, no grayscale, very large open spaces for young children.",
        icon_modifiers="Bold black outline icon with simple fill color, high contrast, clear silhouette.",
    ),
    IllustrationStyle(
        style_name="Minimal Preschool",
        image_prompt_modifiers="Very simple preschool style, few details, rounded friendly shapes, calm colors, uncluttered page.",
        cover_modifiers="Minimal preschool cover scene, one main subject, simple background, generous blank space.",
        coloring_page_modifiers="Very simple outlines, oversized shapes, minimal detail, no shading, no readable text.",
        icon_modifiers="Minimal rounded icon, one simple subject, very low detail, transparent background when possible.",
    ),
]


def _slugify(text: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "_" for character in text).strip("_")
    return slug or "illustration_style"


def ensure_preloaded_styles(output_dir: Path | None = None) -> list[Path]:
    """Write built-in styles to JSON files if they do not already exist."""
    target_dir = output_dir or STYLES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    for style in PRELOADED_STYLES:
        path = target_dir / f"{_slugify(style.style_name)}.json"
        if not path.exists():
            path.write_text(style.model_dump_json(indent=2), encoding="utf-8")
        paths.append(path)
    return paths


def save_style(style: IllustrationStyle, output_dir: Path | None = None) -> Path:
    """Save a custom or edited illustration style as JSON."""
    target_dir = output_dir or STYLES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{_slugify(style.style_name)}.json"
    path.write_text(style.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_styles(output_dir: Path | None = None) -> list[IllustrationStyle]:
    """Load all saved styles, creating preloaded styles first."""
    target_dir = output_dir or STYLES_DIR
    ensure_preloaded_styles(target_dir)

    styles: list[IllustrationStyle] = []
    for path in sorted(target_dir.glob("*.json")):
        styles.append(IllustrationStyle.model_validate_json(path.read_text(encoding="utf-8")))
    return styles


def export_styles_index(output_dir: Path | None = None) -> Path:
    """Save a combined styles index JSON for easy review."""
    target_dir = output_dir or STYLES_DIR
    styles = load_styles(target_dir)
    path = target_dir / "styles_index.json"
    path.write_text(
        json.dumps([style.model_dump() for style in styles], indent=2),
        encoding="utf-8",
    )
    return path
