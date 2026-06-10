from __future__ import annotations


def generate_tracing_activity(
    words: list[str],
    font_size: int = 54,
    repeats: int = 3,
    line_spacing: int = 90,
) -> dict[str, object]:
    """Return large dashed text placeholders for handwriting pages."""
    if not words:
        raise ValueError("At least one tracing word is required.")
    if font_size < 12:
        raise ValueError("font_size must be at least 12.")
    if repeats < 1:
        raise ValueError("repeats must be at least 1.")

    lines = []
    for word_index, word in enumerate(words):
        cleaned = word.strip()
        if not cleaned:
            raise ValueError("Tracing words cannot be blank.")
        for repeat_index in range(repeats):
            lines.append(
                {
                    "text": cleaned,
                    "x": 72,
                    "y": 120 + (word_index * repeats + repeat_index) * line_spacing,
                    "font_size": font_size,
                    "style": "dashed_placeholder",
                    "stroke_width": 1,
                }
            )

    return {
        "activity_type": "tracing",
        "words": [word.strip() for word in words],
        "text_lines": lines,
        "answer_key": None,
    }
