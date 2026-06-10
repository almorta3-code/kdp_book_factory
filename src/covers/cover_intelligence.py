from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.compliance.provenance_engine import record_prompt, update_project_provenance
from src.config import get_settings
from src.openai_client import get_openai_client


class CoverConcept(BaseModel):
    """One ranked cover direction to review before creating image art."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    rank: int = Field(..., ge=1, le=10)
    concept_name: str = Field(..., min_length=3, max_length=120)
    title_placement: str = Field(..., min_length=10, max_length=600)
    focal_character: str = Field(..., min_length=10, max_length=600)
    emotional_hook: str = Field(..., min_length=10, max_length=600)
    color_strategy: str = Field(..., min_length=10, max_length=600)
    composition_notes: str = Field(..., min_length=20, max_length=1000)
    image_prompt: str = Field(..., min_length=40, max_length=1600)
    ranking_reason: str = Field(..., min_length=20, max_length=1000)

    @field_validator(
        "concept_name",
        "title_placement",
        "focal_character",
        "emotional_hook",
        "color_strategy",
        "composition_notes",
        "image_prompt",
        "ranking_reason",
    )
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Cover concept fields cannot be blank.")
        return cleaned


class CoverConceptSet(BaseModel):
    """A ranked set of cover concepts for one niche and audience."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    niche: str = Field(..., min_length=3, max_length=160)
    age_range: str = Field(..., min_length=2, max_length=80)
    style: str = Field(..., min_length=3, max_length=500)
    positioning_summary: str = Field(..., min_length=30, max_length=1000)
    concepts: list[CoverConcept] = Field(..., min_length=10, max_length=10)

    @field_validator("niche", "age_range", "style", "positioning_summary")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Cover concept set fields cannot be blank.")
        return cleaned

    @field_validator("concepts")
    @classmethod
    def validate_rank_order(cls, value: list[CoverConcept]) -> list[CoverConcept]:
        ranks = [concept.rank for concept in value]
        if sorted(ranks) != list(range(1, 11)):
            raise ValueError("Cover concepts must be ranked 1 through 10.")
        return sorted(value, key=lambda concept: concept.rank)


def _system_prompt() -> str:
    return """
You are a senior KDP cover strategist and children's book art director.

Generate cover concepts before image creation.

Rules:
- Produce original concepts only.
- Avoid copyrighted characters, trademarked styles, and readable text inside the image prompt.
- Make the cover instantly understandable at thumbnail size.
- Prioritize parent buyer appeal, child curiosity, educational value, and clear niche signaling.
- The image prompt should describe artwork only; title and subtitle text will be added later in layout.
- Rank concepts from strongest to weakest.
""".strip()


def _user_prompt(niche: str, age_range: str, style: str) -> str:
    return f"""
Create exactly 10 ranked CoverConcept entries for this KDP children's activity workbook.

Niche: {niche}
Age range: {age_range}
Style direction: {style}

For each concept include:
- title placement
- focal character
- emotional hook
- color strategy
- composition notes
- image prompt
- ranking reason

Return concepts ranked from 1 strongest to 10 weakest.
""".strip()


def generate_cover_concepts(niche: str, age_range: str, style: str) -> CoverConceptSet:
    """Generate 10 ranked cover concepts using structured output."""
    cleaned_niche = niche.strip()
    cleaned_age = age_range.strip()
    cleaned_style = style.strip()
    if len(cleaned_niche) < 3:
        raise ValueError("Enter a niche with at least 3 characters.")
    if len(cleaned_age) < 2:
        raise ValueError("Enter an age range.")
    if len(cleaned_style) < 3:
        raise ValueError("Enter a style direction.")

    client = get_openai_client()
    system_prompt = _system_prompt()
    user_prompt = _user_prompt(cleaned_niche, cleaned_age, cleaned_style)

    responses_api = getattr(client, "responses", None)
    if responses_api is not None and hasattr(responses_api, "parse"):
        response = responses_api.parse(
            model=get_settings().model_text_planner,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=CoverConceptSet,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise RuntimeError("OpenAI returned no parsed CoverConceptSet.")
        try:
            record_prompt(
                "cover_intelligence",
                get_settings().model_text_planner,
                f"{system_prompt}\n\n{user_prompt}",
                f"Generated 10 cover concepts for {parsed.niche}",
            )
            update_project_provenance(
                model_used=get_settings().model_text_planner,
                generation_event=f"Generated cover concepts for {parsed.niche}",
            )
        except Exception:
            pass
        return parsed

    completion = client.beta.chat.completions.parse(
        model=get_settings().model_text_planner,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=CoverConceptSet,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("OpenAI returned no parsed CoverConceptSet.")
    try:
        record_prompt(
            "cover_intelligence",
            get_settings().model_text_planner,
            f"{system_prompt}\n\n{user_prompt}",
            f"Generated 10 cover concepts for {parsed.niche}",
        )
        update_project_provenance(
            model_used=get_settings().model_text_planner,
            generation_event=f"Generated cover concepts for {parsed.niche}",
        )
    except Exception:
        pass
    return parsed
