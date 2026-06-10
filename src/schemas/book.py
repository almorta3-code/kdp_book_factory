from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TrimSize = Literal["8.5 x 11 in", "8 x 10 in", "7 x 10 in", "6 x 9 in"]
ColorMode = Literal["Black and white", "Full color", "Interior grayscale"]
Difficulty = Literal["easy", "medium", "hard"]
PageType = Literal[
    "cover",
    "intro",
    "coloring",
    "maze",
    "word_search",
    "dot_to_dot",
    "spot_the_difference",
    "tracing",
    "counting",
    "matching",
    "quiz",
    "story",
    "answer_key",
    "blank",
]
ActivityDataValue = str | int | float | bool | list[str] | list[int] | list[float]
AnswerKeyValue = str | int | float | bool | list[str] | list[int] | list[list[int]]


class StrictSchema(BaseModel):
    """Base schema that rejects unknown fields and avoids silent coercion."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        validate_assignment=True,
    )


class BookRequest(StrictSchema):
    """Complete user request for planning and generating an activity book."""

    theme: str = Field(..., min_length=3, max_length=120)
    age_min: int = Field(..., ge=2, le=14)
    age_max: int = Field(..., ge=2, le=14)
    trim_size: TrimSize
    page_count: int = Field(..., ge=8, le=200)
    color_mode: ColorMode
    activity_types: list[str] = Field(..., min_length=1, max_length=12)
    style_direction: str = Field(..., min_length=3, max_length=500)
    difficulty: Difficulty
    language: str = Field(..., min_length=2, max_length=40)

    @field_validator("theme", "style_direction", "language")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Required text fields cannot be blank.")
        return cleaned

    @field_validator("activity_types")
    @classmethod
    def validate_activity_types(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("Activity types cannot contain blank values.")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Activity types must be unique.")
        return cleaned

    @model_validator(mode="after")
    def validate_age_range(self) -> BookRequest:
        if self.age_min > self.age_max:
            raise ValueError("age_min must be less than or equal to age_max.")
        return self


class BookBlueprintRequest(StrictSchema):
    """User-facing inputs required to plan a workbook."""

    book_theme: str = Field(..., min_length=3, max_length=120)
    age_range: str
    trim_size: TrimSize
    number_of_pages: int = Field(..., ge=8, le=200)
    color_mode: ColorMode
    activity_types: list[str] = Field(..., min_length=1, max_length=12)
    style_direction: str = Field(..., min_length=3, max_length=500)

    @field_validator("book_theme", "style_direction")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Theme and style direction are required.")
        return cleaned


class ContentBlock(StrictSchema):
    """Typed content block for instructions, story text, captions, or callouts."""

    type: str = Field(..., min_length=2, max_length=40)
    text: str = Field(..., min_length=1, max_length=1000)

    @field_validator("type", "text")
    @classmethod
    def strip_content_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Content block fields cannot be blank.")
        return cleaned


class PageSpec(StrictSchema):
    """Detailed specification for a single workbook page."""

    page_number: int = Field(..., ge=1, le=200)
    page_type: PageType
    title: str = Field(..., min_length=1, max_length=120)
    content_blocks: list[ContentBlock] = Field(..., min_length=1, max_length=12)
    required_assets: list[str] = Field(..., max_length=20)
    activity_data: dict[str, ActivityDataValue] = Field(..., max_length=40)
    answer_key: str | dict[str, AnswerKeyValue] | None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Page title cannot be blank.")
        return cleaned


class QuizQuestion(StrictSchema):
    """A child-friendly quiz question with its expected answer."""

    question: str = Field(..., min_length=5, max_length=180)
    answer: str = Field(..., min_length=1, max_length=120)

    @field_validator("question", "answer")
    @classmethod
    def strip_quiz_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Quiz fields cannot be blank.")
        return cleaned


class MatchingPair(StrictSchema):
    """A vocabulary or concept pair for matching activities."""

    left: str = Field(..., min_length=1, max_length=80)
    right: str = Field(..., min_length=1, max_length=160)

    @field_validator("left", "right")
    @classmethod
    def strip_pair_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Matching pair fields cannot be blank.")
        return cleaned


class PlannedActivity(StrictSchema):
    """One planned workbook page or spread."""

    page_number: int
    activity_type: str
    title: str
    learning_goal: str
    generation_notes: str


class BookBlueprint(StrictSchema):
    """Planner output that drives page, asset, and production generation."""

    title: str = Field(..., min_length=3, max_length=120)
    subtitle: str = Field(..., min_length=3, max_length=160)
    audience: str = Field(..., min_length=3, max_length=300)
    promise: str = Field(..., min_length=3, max_length=500)
    unique_angle: str = Field(..., min_length=3, max_length=500)
    animal_or_topic_list: list[str] = Field(..., min_length=1, max_length=100)
    page_plan: list[PageSpec] = Field(..., min_length=1)
    activity_mix: dict[str, int] = Field(..., min_length=1)
    visual_style: str = Field(..., min_length=3, max_length=500)
    kdp_positioning: str = Field(..., min_length=3, max_length=600)

    @field_validator("title", "subtitle", "audience", "promise", "unique_angle", "visual_style", "kdp_positioning")
    @classmethod
    def strip_text_fields(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Text fields cannot be blank.")
        return cleaned

    @field_validator("animal_or_topic_list")
    @classmethod
    def validate_topic_list(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("animal_or_topic_list cannot contain blank values.")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("animal_or_topic_list values must be unique.")
        return cleaned

    @field_validator("activity_mix")
    @classmethod
    def validate_activity_mix(cls, value: dict[str, int]) -> dict[str, int]:
        for activity_type, count in value.items():
            if not activity_type.strip():
                raise ValueError("activity_mix keys cannot be blank.")
            if count < 0:
                raise ValueError("activity_mix counts cannot be negative.")
        return value

    @model_validator(mode="after")
    def validate_page_plan(self) -> BookBlueprint:
        page_numbers = [page.page_number for page in self.page_plan]
        if len(set(page_numbers)) != len(page_numbers):
            raise ValueError("page_plan page numbers must be unique.")
        return self


class AnimalUnit(StrictSchema):
    """Reusable content unit for animal or topic-led workbooks."""

    animal_name: str = Field(..., min_length=1, max_length=80)
    habitat: str = Field(..., min_length=2, max_length=160)
    diet: str = Field(..., min_length=2, max_length=160)
    fun_facts: list[str] = Field(..., min_length=1, max_length=8)
    short_story: str = Field(..., min_length=20, max_length=1200)
    vocabulary_words: list[str] = Field(..., min_length=1, max_length=20)
    activity_ideas: list[str] = Field(..., min_length=1, max_length=12)
    image_prompts: list[str] = Field(..., min_length=1, max_length=12)
    quiz_questions: list[QuizQuestion] = Field(..., min_length=1, max_length=8)
    matching_pairs: list[MatchingPair] = Field(..., min_length=1, max_length=10)
    tracing_words: list[str] = Field(..., min_length=1, max_length=12)
    coloring_page_prompt: str = Field(..., min_length=20, max_length=700)
    flashcard_text: str = Field(..., min_length=10, max_length=400)

    @field_validator("animal_name", "habitat", "diet", "short_story", "coloring_page_prompt", "flashcard_text")
    @classmethod
    def strip_animal_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Animal unit text fields cannot be blank.")
        return cleaned

    @field_validator(
        "fun_facts",
        "vocabulary_words",
        "activity_ideas",
        "image_prompts",
        "tracing_words",
    )
    @classmethod
    def validate_non_empty_lists(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("List values cannot be blank.")
        return cleaned


class ContentUnitBatch(StrictSchema):
    """Structured output wrapper for a list of generated content units."""

    units: list[AnimalUnit] = Field(..., min_length=1, max_length=100)


class KDPMetadata(StrictSchema):
    """Amazon KDP listing metadata drafted alongside the book concept."""

    title: str = Field(..., min_length=3, max_length=200)
    subtitle: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=50, max_length=4000)
    keywords: list[str] = Field(..., min_length=7, max_length=7)
    categories: list[str] = Field(..., min_length=2, max_length=2)
    author_name_placeholder: str = Field(..., min_length=2, max_length=120)
    backend_search_terms: list[str] = Field(..., min_length=1, max_length=50)
    launch_checklist: list[str] = Field(..., min_length=5, max_length=20)

    @field_validator("title", "subtitle", "description", "author_name_placeholder")
    @classmethod
    def strip_metadata_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Metadata text fields cannot be blank.")
        return cleaned

    @field_validator("keywords", "categories", "backend_search_terms", "launch_checklist")
    @classmethod
    def validate_metadata_lists(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("Metadata lists cannot contain blank values.")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Metadata list values must be unique.")
        return cleaned
