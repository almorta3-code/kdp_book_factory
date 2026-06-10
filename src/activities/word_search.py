from __future__ import annotations

import random
import string
from dataclasses import dataclass


Direction = tuple[int, int]


@dataclass(frozen=True)
class WordPlacement:
    """A placed word and the cells that form its answer path."""

    word: str
    direction: str
    start: tuple[int, int]
    end: tuple[int, int]
    cells: list[tuple[int, int]]


DIRECTIONS: dict[str, Direction] = {
    "horizontal": (0, 1),
    "vertical": (1, 0),
    "diagonal_down": (1, 1),
    "diagonal_up": (-1, 1),
}


def _clean_word(word: str) -> str:
    cleaned = "".join(character for character in word.upper() if character.isalpha())
    if not cleaned:
        raise ValueError("Words must contain at least one letter.")
    return cleaned


def _path_for_word(row: int, col: int, direction: Direction, length: int) -> list[tuple[int, int]]:
    row_step, col_step = direction
    return [(row + index * row_step, col + index * col_step) for index in range(length)]


def _fits(grid: list[list[str | None]], word: str, cells: list[tuple[int, int]]) -> bool:
    size = len(grid)
    for letter, (row, col) in zip(word, cells):
        if row < 0 or row >= size or col < 0 or col >= size:
            return False
        existing = grid[row][col]
        if existing is not None and existing != letter:
            return False
    return True


def _place_word(
    grid: list[list[str | None]],
    word: str,
    rng: random.Random,
    allowed_directions: list[str],
) -> WordPlacement:
    size = len(grid)
    candidates: list[tuple[str, int, int]] = []

    for direction_name in allowed_directions:
        for row in range(size):
            for col in range(size):
                candidates.append((direction_name, row, col))

    rng.shuffle(candidates)

    for direction_name, row, col in candidates:
        direction = DIRECTIONS[direction_name]
        cells = _path_for_word(row, col, direction, len(word))
        if not _fits(grid, word, cells):
            continue

        for letter, (cell_row, cell_col) in zip(word, cells):
            grid[cell_row][cell_col] = letter

        return WordPlacement(
            word=word,
            direction=direction_name,
            start=cells[0],
            end=cells[-1],
            cells=cells,
        )

    raise ValueError(f"Could not place word '{word}' in a {size}x{size} grid.")


def generate_word_search(
    words: list[str],
    grid_size: int = 12,
    seed: int | None = None,
    directions: list[str] | None = None,
) -> dict[str, object]:
    """Generate drawable word-search data with placements and answer key."""
    if grid_size < 5:
        raise ValueError("grid_size must be at least 5.")

    cleaned_words = [_clean_word(word) for word in words]
    if not cleaned_words:
        raise ValueError("At least one word is required.")
    if any(len(word) > grid_size for word in cleaned_words):
        raise ValueError("Every word must fit within the grid size.")

    allowed_directions = directions or list(DIRECTIONS)
    unknown_directions = set(allowed_directions) - set(DIRECTIONS)
    if unknown_directions:
        raise ValueError(f"Unknown directions: {sorted(unknown_directions)}")

    rng = random.Random(seed)
    grid: list[list[str | None]] = [[None for _ in range(grid_size)] for _ in range(grid_size)]
    placements = [
        _place_word(grid, word, rng, allowed_directions)
        for word in sorted(cleaned_words, key=len, reverse=True)
    ]

    for row in range(grid_size):
        for col in range(grid_size):
            if grid[row][col] is None:
                grid[row][col] = rng.choice(string.ascii_uppercase)

    answer_key = {
        placement.word: {
            "direction": placement.direction,
            "start": {"row": placement.start[0], "col": placement.start[1]},
            "end": {"row": placement.end[0], "col": placement.end[1]},
            "cells": [{"row": row, "col": col} for row, col in placement.cells],
        }
        for placement in placements
    }

    return {
        "activity_type": "word_search",
        "grid_size": grid_size,
        "grid": ["".join(row) for row in grid],
        "words": cleaned_words,
        "placements": list(answer_key.values()),
        "answer_key": answer_key,
    }


def create_word_search_plan(words: list[str] | None = None, grid_size: int = 12) -> dict[str, object]:
    """Compatibility wrapper used by early scaffold code."""
    return generate_word_search(words or ["READ", "PLAY", "LEARN"], grid_size=grid_size)
