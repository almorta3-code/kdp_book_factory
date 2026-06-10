from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.config import get_settings
from src.openai_client import get_openai_client


class NicheResearchResult(BaseModel):
    """Structured publishing research result for an activity workbook niche."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    niche_name: str = Field(..., min_length=3, max_length=120)
    audience: str = Field(..., min_length=3, max_length=240)
    search_intent: str = Field(..., min_length=3, max_length=400)
    educational_value_score: int = Field(..., ge=1, le=10)
    evergreen_score: int = Field(..., ge=1, le=10)
    seasonality_score: int = Field(..., ge=1, le=10)
    series_potential_score: int = Field(..., ge=1, le=10)
    monetization_score: int = Field(..., ge=1, le=10)
    competition_estimate: str = Field(..., min_length=3, max_length=120)
    overall_score: int = Field(..., ge=1, le=100)
    reasoning: str = Field(..., min_length=20, max_length=2000)
    strengths: list[str] = Field(..., min_length=1, max_length=8)
    weaknesses: list[str] = Field(..., min_length=1, max_length=8)
    recommendation: str = Field(..., min_length=10, max_length=800)

    @field_validator(
        "niche_name",
        "audience",
        "search_intent",
        "competition_estimate",
        "reasoning",
        "recommendation",
    )
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Research text fields cannot be blank.")
        return cleaned

    @field_validator("strengths", "weaknesses")
    @classmethod
    def strip_list_items(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("Research lists cannot contain blank values.")
        return cleaned


def _system_prompt() -> str:
    return """
You are a senior publishing strategist for KDP children's activity workbooks.

Evaluate workbook niche ideas for practical publishing potential. Be realistic and specific, not hype-driven.

Score the niche across:
1. Demand
2. Competition
3. Monetization
4. Expansion potential
5. Cross-platform potential

Use the schema fields to express these judgments:
- educational_value_score reflects learning usefulness.
- evergreen_score reflects long-term demand.
- seasonality_score reflects whether timing helps or limits demand.
- series_potential_score reflects expansion potential.
- monetization_score reflects pricing, bundles, formats, and platform potential.
- competition_estimate should be Low, Medium, High, or Very High with a short qualifier.
- overall_score should be 1 to 100 and calibrated conservatively.

Avoid copyrighted characters, trademarked styles, and brand-dependent niches.
""".strip()


def _user_prompt(topic: str) -> str:
    return f"""
Analyze this activity workbook niche idea:

{topic}

Return a structured niche research result with clear strengths, weaknesses, and a recommendation. Include search intent and whether the niche could work as a series across KDP, Etsy printables, classroom packs, and seasonal bundles.
""".strip()


def analyze_niche(topic: str) -> NicheResearchResult:
    """Analyze a workbook niche idea using structured OpenAI output."""
    cleaned_topic = topic.strip()
    if len(cleaned_topic) < 3:
        raise ValueError("Enter a niche idea with at least 3 characters.")

    client = get_openai_client()
    settings = get_settings()
    system_prompt = _system_prompt()
    user_prompt = _user_prompt(cleaned_topic)

    responses_api = getattr(client, "responses", None)
    if responses_api is not None and hasattr(responses_api, "parse"):
        response = responses_api.parse(
            model=settings.model_text_planner,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=NicheResearchResult,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise RuntimeError("OpenAI returned no parsed niche research result.")
        return parsed

    completion = client.beta.chat.completions.parse(
        model=settings.model_text_planner,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=NicheResearchResult,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("OpenAI returned no parsed niche research result.")
    return parsed


def _slugify(text: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "_" for character in text).strip("_")
    return slug or "niche_research"


def save_niche_research_result(result: NicheResearchResult, output_dir: Path | None = None) -> Path:
    """Save niche research results under outputs/research."""
    target_dir = output_dir or (get_settings().outputs_dir / "research")
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_path = target_dir / f"{timestamp}_{_slugify(result.niche_name)}.json"
    output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return output_path
