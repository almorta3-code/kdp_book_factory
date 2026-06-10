from __future__ import annotations

import random
from collections.abc import Sequence


def _normalize_pair(pair: tuple[str, str] | dict[str, str]) -> tuple[str, str]:
    if isinstance(pair, dict):
        left = pair.get("left")
        right = pair.get("right")
    else:
        left, right = pair

    if not left or not right:
        raise ValueError("Matching pairs must include left and right text.")
    return left.strip(), right.strip()


def generate_matching_activity(
    pairs: Sequence[tuple[str, str] | dict[str, str]],
    seed: int | None = None,
) -> dict[str, object]:
    """Randomize matching columns and return a clear answer key."""
    if not pairs:
        raise ValueError("At least one matching pair is required.")

    rng = random.Random(seed)
    normalized_pairs = [_normalize_pair(pair) for pair in pairs]
    left_values = [left for left, _ in normalized_pairs]
    right_values = [right for _, right in normalized_pairs]
    if len(set(left_values)) != len(left_values):
        raise ValueError("Matching left values must be unique.")
    if len(set(right_values)) != len(right_values):
        raise ValueError("Matching right values must be unique.")

    left_items = [{"id": f"L{index + 1}", "text": left} for index, (left, _) in enumerate(normalized_pairs)]
    right_items = [{"id": f"R{index + 1}", "text": right} for index, (_, right) in enumerate(normalized_pairs)]

    rng.shuffle(left_items)
    rng.shuffle(right_items)

    original_lookup = {left: right for left, right in normalized_pairs}
    right_id_by_text = {item["text"]: item["id"] for item in right_items}
    answer_key = {
        left_item["id"]: right_id_by_text[original_lookup[left_item["text"]]]
        for left_item in left_items
    }

    return {
        "activity_type": "matching",
        "left_column": left_items,
        "right_column": right_items,
        "answer_key": answer_key,
    }
