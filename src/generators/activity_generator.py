from __future__ import annotations

import json
from pathlib import Path

from src.activities import (
    generate_dot_to_dot,
    generate_matching_activity,
    generate_maze,
    generate_quiz_activity,
    generate_tracing_activity,
    generate_word_search,
)
from src.compliance.provenance_engine import record_output_file, update_project_provenance
from src.config import get_settings
from src.schemas.book import AnimalUnit, BookBlueprint


def _unit_for_page(content_units: list[AnimalUnit], page_number: int) -> AnimalUnit:
    index = (page_number - 1) % len(content_units)
    return content_units[index]


def _quiz_payload(unit: AnimalUnit) -> list[dict[str, object]]:
    questions = []
    fallback_answers = [word for word in unit.vocabulary_words[:4] if word]
    for question in unit.quiz_questions[:4]:
        distractors = [answer for answer in fallback_answers if answer.lower() != question.answer.lower()]
        while len(distractors) < 2:
            distractors.append(f"Not {question.answer}")
        questions.append(
            {
                "question": question.question,
                "answer": question.answer,
                "distractors": distractors[:3],
            }
        )
    return questions


def generate_activity_data(
    blueprint: BookBlueprint,
    content_units: list[AnimalUnit],
    seed: int = 42,
) -> dict[str, object]:
    """Generate deterministic drawable activity data for planned activity pages."""
    if not content_units:
        raise ValueError("Content units are required before generating activity data.")

    activity_pages: dict[str, object] = {}
    for page in blueprint.page_plan:
        page_type = page.page_type
        unit = _unit_for_page(content_units, page.page_number)
        page_seed = seed + page.page_number

        if page_type == "word_search":
            words = unit.vocabulary_words[:8] or [unit.animal_name]
            payload = generate_word_search(words, grid_size=10, seed=page_seed)
        elif page_type == "maze":
            payload = generate_maze(width=10, height=10, seed=page_seed)
        elif page_type == "dot_to_dot":
            payload = generate_dot_to_dot(unit.animal_name, point_count=24)
        elif page_type == "matching":
            pairs = [{"left": pair.left, "right": pair.right} for pair in unit.matching_pairs]
            payload = generate_matching_activity(pairs, seed=page_seed)
        elif page_type == "tracing":
            payload = generate_tracing_activity(unit.tracing_words[:5] or unit.vocabulary_words[:5])
        elif page_type == "counting":
            payload = {
                "activity_type": "counting",
                "prompt": f"Count the {unit.animal_name} shapes.",
                "count_target": 10,
                "answer_key": {"count": 10},
            }
        elif page_type == "story":
            payload = {
                "activity_type": "story",
                "prompt": unit.short_story,
                "answer_key": None,
            }
        else:
            continue

        activity_pages[str(page.page_number)] = {
            "page_number": page.page_number,
            "title": page.title,
            **payload,
        }

    return {"pages": activity_pages}


def save_activity_data(activity_data: dict[str, object], output_dir: Path | None = None) -> Path:
    """Save generated activity data to the active project."""
    target_dir = output_dir or (get_settings().outputs_dir / "current_project")
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / "activity_data.json"
    output_path.write_text(json.dumps(activity_data, indent=2), encoding="utf-8")
    return output_path


def generate_and_save_activity_data(blueprint: BookBlueprint, content_units: list[AnimalUnit]) -> tuple[dict[str, object], Path]:
    """Generate and persist activity data in one step."""
    activity_data = generate_activity_data(blueprint, content_units)
    output_path = save_activity_data(activity_data)
    try:
        record_output_file(output_path)
        update_project_provenance(book_title=blueprint.title, generation_event="Generated deterministic activity data", output_file=output_path)
    except Exception:
        pass
    return activity_data, output_path
