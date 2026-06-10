from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.config import get_settings
from src.openai_client import get_openai_client
from src.schemas.book import AnimalUnit, BookBlueprint


SupportedLanguage = Literal["English", "French", "Spanish", "German", "Arabic"]
SUPPORTED_LANGUAGES: tuple[str, ...] = ("English", "French", "Spanish", "German", "Arabic")


class TranslatedQuizQuestion(BaseModel):
    """Translated quiz question and answer."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    question: str = Field(..., min_length=2, max_length=220)
    answer: str = Field(..., min_length=1, max_length=160)

    @field_validator("question", "answer")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Translated quiz fields cannot be blank.")
        return cleaned


class TranslatedMatchingPair(BaseModel):
    """Translated matching activity pair."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    left: str = Field(..., min_length=1, max_length=120)
    right: str = Field(..., min_length=1, max_length=220)

    @field_validator("left", "right")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Translated matching fields cannot be blank.")
        return cleaned


class TranslatedUnit(BaseModel):
    """Translated content unit for one animal or topic."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    original_name: str = Field(..., min_length=1, max_length=100)
    translated_name: str = Field(..., min_length=1, max_length=120)
    habitat: str = Field(..., min_length=2, max_length=220)
    diet: str = Field(..., min_length=2, max_length=220)
    story: str = Field(..., min_length=20, max_length=1500)
    facts: list[str] = Field(..., min_length=1, max_length=8)
    quiz_questions: list[TranslatedQuizQuestion] = Field(..., min_length=1, max_length=8)
    flashcard_text: str = Field(..., min_length=10, max_length=600)
    tracing_words: list[str] = Field(..., min_length=1, max_length=20)
    vocabulary_words: list[str] = Field(..., min_length=1, max_length=20)
    matching_pairs: list[TranslatedMatchingPair] = Field(..., min_length=1, max_length=10)

    @field_validator("original_name", "translated_name", "habitat", "diet", "story", "flashcard_text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Translated text fields cannot be blank.")
        return cleaned

    @field_validator("facts", "tracing_words", "vocabulary_words")
    @classmethod
    def strip_list_items(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("Translated lists cannot contain blank values.")
        return cleaned


class LanguagePack(BaseModel):
    """Complete translated project content for one language."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    language: SupportedLanguage
    translated_title: str = Field(..., min_length=3, max_length=160)
    translated_subtitle: str = Field(..., min_length=3, max_length=220)
    age_appropriateness_notes: str = Field(..., min_length=10, max_length=800)
    units: list[TranslatedUnit] = Field(..., min_length=1, max_length=100)

    @field_validator("translated_title", "translated_subtitle", "age_appropriateness_notes")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Language pack text fields cannot be blank.")
        return cleaned


def _system_prompt() -> str:
    return """
You are a children's educational localization editor.

Translate workbook content while preserving age appropriateness, simple vocabulary, and activity usefulness.

Rules:
- Keep wording natural for children in the target language.
- Preserve educational meaning, not word-for-word awkward phrasing.
- Tracing words should be short, useful, and appropriate for handwriting practice.
- Quiz questions must still have clear correct answers.
- Matching pairs must remain simple and child-friendly.
- Avoid copyrighted characters, trademarked references, or adult phrasing.
- For Arabic, use natural Modern Standard Arabic suitable for children.
""".strip()


def _user_prompt(blueprint: BookBlueprint, content_units: list[AnimalUnit], language: str) -> str:
    source_units = [
        {
            "animal_name": unit.animal_name,
            "habitat": unit.habitat,
            "diet": unit.diet,
            "story": unit.short_story,
            "facts": unit.fun_facts,
            "quiz_questions": [question.model_dump() for question in unit.quiz_questions],
            "flashcard_text": unit.flashcard_text,
            "tracing_words": unit.tracing_words,
            "vocabulary_words": unit.vocabulary_words,
            "matching_pairs": [pair.model_dump() for pair in unit.matching_pairs],
        }
        for unit in content_units
    ]

    return f"""
Translate this workbook project into {language}.

Title: {blueprint.title}
Subtitle: {blueprint.subtitle}
Audience: {blueprint.audience}

Translate stories, facts, quizzes, flashcards, tracing words, vocabulary words, and matching pairs.
Maintain age appropriateness for the same audience.

Source units:
{source_units}
""".strip()


def translate_project(
    blueprint: BookBlueprint,
    content_units: list[AnimalUnit],
    language: SupportedLanguage,
) -> LanguagePack:
    """Translate the complete project content into one supported language."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    if not content_units:
        raise ValueError("Content units are required before translation.")

    client = get_openai_client()
    system_prompt = _system_prompt()
    user_prompt = _user_prompt(blueprint, content_units, language)

    responses_api = getattr(client, "responses", None)
    if responses_api is not None and hasattr(responses_api, "parse"):
        response = responses_api.parse(
            model=get_settings().model_text_fast,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=LanguagePack,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise RuntimeError("OpenAI returned no parsed LanguagePack.")
        return parsed

    completion = client.beta.chat.completions.parse(
        model=get_settings().model_text_fast,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=LanguagePack,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("OpenAI returned no parsed LanguagePack.")
    return parsed


def _language_filename(language: str) -> str:
    return language.strip().lower().replace(" ", "_") + ".json"


def save_language_pack(pack: LanguagePack, output_dir: Path | None = None) -> Path:
    """Save a language pack as english.json, french.json, and so on."""
    target_dir = output_dir or (get_settings().outputs_dir / "current_project" / "language_packs")
    target_dir.mkdir(parents=True, exist_ok=True)

    output_path = target_dir / _language_filename(pack.language)
    output_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")
    return output_path
