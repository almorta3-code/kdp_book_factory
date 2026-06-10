from __future__ import annotations

from pathlib import Path

from src.config import get_settings
from src.compliance.provenance_engine import record_prompt, update_project_provenance
from src.google_client import generate_structured
from src.schemas.book import AnimalUnit, BookBlueprint, ContentUnitBatch


def _build_system_prompt() -> str:
    """Define the content writer role and safety constraints."""
    return """
You are a children's educational content writer for KDP activity workbooks.

Create original, age-appropriate, classroom-friendly content units for each animal or topic in a workbook blueprint.

Rules:
- Avoid copyrighted characters, branded worlds, trademarked styles, and celebrity references.
- Keep facts simple, accurate, and suitable for young children.
- Make every story warm, original, and about 80 words.
- Use simple vocabulary that can become tracing, matching, flashcards, and puzzles.
- Keep image prompts safe, printable, and consistent with the blueprint visual style.
- Use clear quiz questions with child-friendly wording.
- Matching pairs must connect a simple word or concept to a simple meaning.
""".strip()


def _build_user_prompt(blueprint: BookBlueprint) -> str:
    """Turn the blueprint into a focused content-generation brief."""
    topics = ", ".join(blueprint.animal_or_topic_list)

    return f"""
Generate one AnimalUnit for each animal or topic in this list:
{topics}

Book title: {blueprint.title}
Subtitle: {blueprint.subtitle}
Audience: {blueprint.audience}
Promise: {blueprint.promise}
Unique angle: {blueprint.unique_angle}
Visual style: {blueprint.visual_style}
KDP positioning: {blueprint.kdp_positioning}

For each unit, include:
- an 80-word short_story
- exactly 5 simple fun_facts
- vocabulary_words for puzzles and tracing
- quiz_questions with answers
- matching_pairs with left and right values
- tracing_words
- image_prompts for supporting assets
- one coloring_page_prompt
- flashcard_text

If the topic is not an animal, put the topic name in animal_name and use habitat/diet as simple contextual fields.
""".strip()


def _parse_structured_response(blueprint: BookBlueprint) -> ContentUnitBatch:
    """Call Gemini structured outputs and parse content units."""
    settings = get_settings()
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(blueprint)
    parsed = generate_structured(settings.model_text_fast, system_prompt, user_prompt, ContentUnitBatch)
    try:
        record_prompt(
            "content_generator",
            settings.model_text_fast,
            f"{system_prompt}\n\n{user_prompt}",
            f"Generated {len(parsed.units)} content units",
        )
        update_project_provenance(
            book_title=blueprint.title,
            model_used=settings.model_text_fast,
            generation_event="Generated book content units",
        )
    except Exception:
        pass
    return parsed


def _validate_units_against_blueprint(units: list[AnimalUnit], blueprint: BookBlueprint) -> None:
    """Ensure the content stage covers every planned animal or topic."""
    expected = blueprint.animal_or_topic_list
    received = [unit.animal_name for unit in units]

    if len(received) != len(expected):
        raise ValueError(
            "Content unit count must match animal_or_topic_list count: "
            f"expected {len(expected)}, received {len(received)}."
        )


def save_content_units(units: list[AnimalUnit], output_dir: Path | None = None) -> Path:
    """Save generated content units for downstream page and asset generation."""
    target_dir = output_dir or (get_settings().outputs_dir / "current_project")
    target_dir.mkdir(parents=True, exist_ok=True)

    output_path = target_dir / "content_units.json"
    content_json = ContentUnitBatch(units=units).model_dump_json(indent=2)
    output_path.write_text(content_json, encoding="utf-8")
    return output_path


def generate_content_units(blueprint: BookBlueprint) -> list[AnimalUnit]:
    """Generate and save structured content units for the current blueprint."""
    batch = _parse_structured_response(blueprint)
    _validate_units_against_blueprint(batch.units, blueprint)
    save_content_units(batch.units)
    return batch.units
