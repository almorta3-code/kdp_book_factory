from src.activities.maze import generate_maze
from src.activities.word_search import generate_word_search


def test_word_search_places_words_and_answer_key() -> None:
    result = generate_word_search(["cat", "dog"], grid_size=8, seed=7)

    assert result["grid_size"] == 8
    assert len(result["grid"]) == 8
    assert all(len(row) == 8 for row in result["grid"])
    assert set(result["answer_key"]) == {"CAT", "DOG"}

    for word, answer in result["answer_key"].items():
        cells = answer["cells"]
        letters = "".join(result["grid"][cell["row"]][cell["col"]] for cell in cells)
        assert letters == word


def test_maze_has_solution_and_wall_coordinates() -> None:
    result = generate_maze(width=6, height=5, seed=3)

    assert result["width"] == 6
    assert result["height"] == 5
    assert result["wall_coordinates"]

    solution = result["answer_key"]["solution_path"]
    assert solution[0] == {"row": 0, "col": 0}
    assert solution[-1] == {"row": 4, "col": 5}
