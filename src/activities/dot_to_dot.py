from __future__ import annotations

import math


def _ellipse_points(count: int, width: float, height: float) -> list[tuple[float, float]]:
    center_x = width / 2
    center_y = height / 2
    radius_x = width * 0.34
    radius_y = height * 0.28

    return [
        (
            center_x + math.cos(2 * math.pi * index / count) * radius_x,
            center_y + math.sin(2 * math.pi * index / count) * radius_y,
        )
        for index in range(count)
    ]


def _fish_points(count: int, width: float, height: float) -> list[tuple[float, float]]:
    body_count = max(6, count - 3)
    points = _ellipse_points(body_count, width * 0.82, height)
    tail_x = width * 0.88
    center_y = height / 2
    tail = [(tail_x, center_y), (width * 0.98, height * 0.28), (width * 0.98, height * 0.72)]
    return [*points, *tail][:count]


def generate_dot_to_dot(
    topic: str,
    point_count: int = 24,
    width: float = 700,
    height: float = 900,
) -> dict[str, object]:
    """Generate numbered coordinate points around a simple placeholder silhouette."""
    if point_count < 6:
        raise ValueError("point_count must be at least 6.")

    cleaned_topic = topic.strip()
    if not cleaned_topic:
        raise ValueError("topic cannot be blank.")

    topic_key = cleaned_topic.lower()
    points = _fish_points(point_count, width, height) if "fish" in topic_key else _ellipse_points(point_count, width, height)

    return {
        "activity_type": "dot_to_dot",
        "topic": cleaned_topic,
        "silhouette_placeholder": "fish" if "fish" in topic_key else "rounded_animal_body",
        "canvas": {"width": width, "height": height},
        "points": [
            {
                "number": index + 1,
                "label": str(index + 1),
                "x": round(x, 2),
                "y": round(y, 2),
            }
            for index, (x, y) in enumerate(points)
        ],
        "answer_key": {
            "connect_order": list(range(1, len(points) + 1)),
            "close_shape": True,
        },
    }


def create_dot_to_dot_plan(topic: str = "animal") -> dict[str, object]:
    """Compatibility wrapper used by early scaffold code."""
    return generate_dot_to_dot(topic=topic)
