from src.generators.blueprint import build_blueprint_prompt
from src.schemas.book import BookBlueprintRequest, BookRequest


def test_build_blueprint_prompt_includes_core_fields() -> None:
    request = BookBlueprintRequest(
        book_theme="Ocean animals",
        age_range="5-7",
        trim_size="8.5 x 11 in",
        number_of_pages=48,
        color_mode="Black and white",
        activity_types=["Mazes", "Word searches"],
        style_direction="Cute bold outlines",
    )

    prompt = build_blueprint_prompt(request)

    assert "Ocean animals" in prompt
    assert "5-7" in prompt
    assert "Mazes, Word searches" in prompt
    assert "Do not claim" in prompt


def test_book_request_rejects_unknown_fields() -> None:
    try:
        BookRequest(
            theme="Ocean animals",
            age_min=5,
            age_max=7,
            trim_size="8.5 x 11 in",
            page_count=48,
            color_mode="Black and white",
            activity_types=["Mazes"],
            style_direction="Cute bold outlines",
            difficulty="easy",
            language="English",
            unexpected="value",
        )
    except ValueError as exc:
        assert "Extra inputs are not permitted" in str(exc)
    else:
        raise AssertionError("BookRequest accepted an unknown field.")
