from __future__ import annotations

from src.config import get_settings
from src.compliance.provenance_engine import record_prompt, update_project_provenance
from src.google_client import generate_structured
from src.schemas.book import BookBlueprint, BookRequest


def _build_system_prompt() -> str:
    """Define the planner role and non-negotiable production rules."""
    return """
You are a senior KDP niche strategist, children's educational book designer, and activity workbook expert.

Plan differentiated KDP-ready children's activity workbooks with clear learning value, market positioning, and complete production structure.

Rules:
- Create a strong, specific hook that makes the book feel meaningfully different from generic activity books.
- Avoid copyrighted characters, celebrity names, branded worlds, and trademarked visual styles.
- Keep every page age appropriate for the requested age range and difficulty.
- Make the educational value clear through vocabulary, fine motor practice, problem solving, observation, memory, counting, or early literacy.
- Include a full page-by-page plan with one PageSpec for every requested page.
- Include upload package positioning in kdp_positioning, covering customer promise, niche angle, and listing direction.
- Use practical activity_data that later deterministic generators can consume.
- Keep image and asset descriptions original, simple, and safe for children.
""".strip()


def _build_user_prompt(request: BookRequest) -> str:
    """Turn the user's request into a structured planning brief."""
    activity_types = ", ".join(request.activity_types)

    return f"""
Create a complete BookBlueprint for this KDP activity book request.

Theme: {request.theme}
Age range: {request.age_min}-{request.age_max}
Trim size: {request.trim_size}
Page count: {request.page_count}
Color mode: {request.color_mode}
Activity types: {activity_types}
Style direction: {request.style_direction}
Difficulty: {request.difficulty}
Language: {request.language}

Blueprint requirements:
- The page_plan must contain exactly {request.page_count} pages.
- Page numbers must start at 1 and end at {request.page_count}.
- Include front matter, activity pages, and answer-key pages when useful.
- Use specific page titles instead of repeated generic titles.
- Make activity_mix counts match the planned activity pages.
- Use animal_or_topic_list to define the core recurring subjects.
- Make the hook and unique_angle commercially useful for KDP, not vague.
""".strip()


def _parse_structured_response(request: BookRequest) -> BookBlueprint:
    """Call Gemini structured outputs and parse directly into BookBlueprint."""
    settings = get_settings()
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(request)
    parsed = generate_structured(settings.model_text_planner, system_prompt, user_prompt, BookBlueprint)
    try:
        record_prompt(
            "blueprint_generator",
            settings.model_text_planner,
            f"{system_prompt}\n\n{user_prompt}",
            f"Generated blueprint for {parsed.title}",
        )
        update_project_provenance(
            project_name=request.theme,
            book_title=parsed.title,
            language=request.language,
            model_used=settings.model_text_planner,
            generation_event="Generated book blueprint",
        )
    except Exception:
        pass
    return parsed


def _validate_page_plan_against_request(blueprint: BookBlueprint, request: BookRequest) -> None:
    """Guard the app from accepting incomplete page plans."""
    page_numbers = [page.page_number for page in blueprint.page_plan]
    expected_page_numbers = list(range(1, request.page_count + 1))

    if page_numbers != expected_page_numbers:
        raise ValueError(
            "Blueprint page_plan must contain every page number from "
            f"1 to {request.page_count} in order."
        )


def generate_book_blueprint(request: BookRequest) -> BookBlueprint:
    """Generate a structured, validated KDP workbook blueprint."""
    blueprint = _parse_structured_response(request)
    _validate_page_plan_against_request(blueprint, request)
    return blueprint
