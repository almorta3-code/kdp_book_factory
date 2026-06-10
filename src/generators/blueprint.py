from __future__ import annotations

from src.config import get_settings
from src.google_client import generate_text
from src.schemas.book import BookBlueprintRequest


def build_blueprint_prompt(request: BookBlueprintRequest) -> str:
    """Build the planner prompt without performing generation."""
    activities = ", ".join(request.activity_types)

    return f"""
Create a KDP children's activity workbook blueprint.

Theme: {request.book_theme}
Age range: {request.age_range}
Trim size: {request.trim_size}
Number of pages: {request.number_of_pages}
Color mode: {request.color_mode}
Activity types: {activities}
Style direction: {request.style_direction}

Return a concise production blueprint with:
- working title and subtitle
- audience notes
- page allocation by activity type
- safety and age-appropriateness notes
- layout considerations for KDP printing
- asset generation notes

Do not claim that final pages, images, puzzles, or PDFs have been created.
""".strip()


def generate_book_blueprint(request: BookBlueprintRequest) -> str:
    """Call the planner model and return the blueprint text."""
    settings = get_settings()
    return generate_text(settings.model_text_planner, "", build_blueprint_prompt(request))
