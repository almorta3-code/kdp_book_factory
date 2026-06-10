from __future__ import annotations

import random


Cell = tuple[int, int]
WallName = str


DIRECTIONS: dict[WallName, tuple[int, int, WallName]] = {
    "north": (-1, 0, "south"),
    "east": (0, 1, "west"),
    "south": (1, 0, "north"),
    "west": (0, -1, "east"),
}


def _new_cells(width: int, height: int) -> dict[Cell, set[WallName]]:
    return {
        (row, col): {"north", "east", "south", "west"}
        for row in range(height)
        for col in range(width)
    }


def _neighbors(row: int, col: int, width: int, height: int) -> list[tuple[WallName, Cell, WallName]]:
    neighbors: list[tuple[WallName, Cell, WallName]] = []
    for wall, (row_step, col_step, opposite_wall) in DIRECTIONS.items():
        next_row = row + row_step
        next_col = col + col_step
        if 0 <= next_row < height and 0 <= next_col < width:
            neighbors.append((wall, (next_row, next_col), opposite_wall))
    return neighbors


def _solve_maze(cells: dict[Cell, set[WallName]], start: Cell, end: Cell) -> list[Cell]:
    stack: list[tuple[Cell, list[Cell]]] = [(start, [start])]
    visited: set[Cell] = set()

    while stack:
        current, path = stack.pop()
        if current == end:
            return path
        if current in visited:
            continue
        visited.add(current)

        row, col = current
        for wall, (row_step, col_step, _) in DIRECTIONS.items():
            if wall in cells[current]:
                continue
            neighbor = (row + row_step, col + col_step)
            if neighbor not in visited:
                stack.append((neighbor, [*path, neighbor]))

    return []


def _wall_coordinates(cells: dict[Cell, set[WallName]], width: int, height: int) -> list[dict[str, int]]:
    wall_set: set[tuple[int, int, int, int]] = set()

    for (row, col), walls in cells.items():
        x = col
        y = row
        if "north" in walls:
            wall_set.add((x, y, x + 1, y))
        if "east" in walls:
            wall_set.add((x + 1, y, x + 1, y + 1))
        if "south" in walls:
            wall_set.add((x, y + 1, x + 1, y + 1))
        if "west" in walls:
            wall_set.add((x, y, x, y + 1))

    return [
        {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
        for x1, y1, x2, y2 in sorted(wall_set)
    ]


def generate_maze(
    width: int = 10,
    height: int = 10,
    seed: int | None = None,
    start: Cell = (0, 0),
    end: Cell | None = None,
) -> dict[str, object]:
    """Generate a rectangular DFS maze and return drawable wall coordinates."""
    if width < 2 or height < 2:
        raise ValueError("Maze width and height must be at least 2.")

    end = end or (height - 1, width - 1)
    if start[0] not in range(height) or start[1] not in range(width):
        raise ValueError("Maze start must be inside the grid.")
    if end[0] not in range(height) or end[1] not in range(width):
        raise ValueError("Maze end must be inside the grid.")

    rng = random.Random(seed)
    cells = _new_cells(width, height)
    visited = {start}
    stack = [start]

    while stack:
        current = stack[-1]
        row, col = current
        unvisited = [
            (wall, neighbor, opposite_wall)
            for wall, neighbor, opposite_wall in _neighbors(row, col, width, height)
            if neighbor not in visited
        ]

        if not unvisited:
            stack.pop()
            continue

        wall, neighbor, opposite_wall = rng.choice(unvisited)
        cells[current].remove(wall)
        cells[neighbor].remove(opposite_wall)
        visited.add(neighbor)
        stack.append(neighbor)

    solution = _solve_maze(cells, start, end)

    return {
        "activity_type": "maze",
        "width": width,
        "height": height,
        "start": {"row": start[0], "col": start[1]},
        "end": {"row": end[0], "col": end[1]},
        "wall_coordinates": _wall_coordinates(cells, width, height),
        "cells": [
            {"row": row, "col": col, "walls": sorted(walls)}
            for (row, col), walls in sorted(cells.items())
        ],
        "answer_key": {
            "solution_path": [{"row": row, "col": col} for row, col in solution],
        },
    }


def create_maze_plan(width: int = 10, height: int = 10) -> dict[str, object]:
    """Compatibility wrapper used by early scaffold code."""
    return generate_maze(width=width, height=height)
