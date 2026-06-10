from __future__ import annotations

import random
from collections.abc import Sequence


def _normalize_question(question: dict[str, object]) -> dict[str, object]:
    prompt = str(question.get("question", "")).strip()
    answer = str(question.get("answer", "")).strip()
    distractors = [str(item).strip() for item in question.get("distractors", [])]

    if not prompt or not answer:
        raise ValueError("Quiz questions must include question and answer.")
    if len(distractors) < 2:
        raise ValueError("Each quiz question needs at least two distractors.")
    if any(not distractor for distractor in distractors):
        raise ValueError("Quiz distractors cannot be blank.")
    if answer in distractors:
        raise ValueError("Quiz distractors must not repeat the correct answer.")
    if len(set(distractors)) != len(distractors):
        raise ValueError("Quiz distractors must be unique.")

    return {"question": prompt, "answer": answer, "distractors": distractors}


def generate_quiz_activity(
    questions: Sequence[dict[str, object]],
    seed: int | None = None,
) -> dict[str, object]:
    """Create multiple-choice quiz data with an answer key."""
    if not questions:
        raise ValueError("At least one quiz question is required.")

    rng = random.Random(seed)
    normalized_questions = [_normalize_question(question) for question in questions]
    items = []
    answer_key = {}

    for index, question in enumerate(normalized_questions, start=1):
        options = [question["answer"], *question["distractors"]]
        unique_options = list(dict.fromkeys(options))
        rng.shuffle(unique_options)

        option_rows = [
            {"id": chr(65 + option_index), "text": option}
            for option_index, option in enumerate(unique_options)
        ]
        correct_option = next(option for option in option_rows if option["text"] == question["answer"])
        question_id = f"Q{index}"

        items.append(
            {
                "id": question_id,
                "question": question["question"],
                "options": option_rows,
            }
        )
        answer_key[question_id] = correct_option["id"]

    return {
        "activity_type": "quiz",
        "questions": items,
        "answer_key": answer_key,
    }
