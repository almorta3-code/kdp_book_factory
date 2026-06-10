"""Deterministic activity generators that return drawable data."""

from src.activities.dot_to_dot import generate_dot_to_dot
from src.activities.matching import generate_matching_activity
from src.activities.maze import generate_maze
from src.activities.quiz import generate_quiz_activity
from src.activities.tracing import generate_tracing_activity
from src.activities.word_search import generate_word_search

__all__ = [
    "generate_dot_to_dot",
    "generate_matching_activity",
    "generate_maze",
    "generate_quiz_activity",
    "generate_tracing_activity",
    "generate_word_search",
]
