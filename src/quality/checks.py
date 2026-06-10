from __future__ import annotations

from src.schemas.book import BookBlueprintRequest


def validate_blueprint_request(request: BookBlueprintRequest) -> list[str]:
    """Return warnings that should be reviewed before full generation."""
    warnings: list[str] = []

    if request.number_of_pages % 2 != 0:
        warnings.append("KDP interiors usually work best with an even page count.")

    return warnings
