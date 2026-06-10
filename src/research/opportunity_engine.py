from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.config import get_settings
from src.openai_client import get_openai_client


class OpportunityScore(BaseModel):
    """Comparable opportunity score for one workbook niche."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    niche_name: str = Field(..., min_length=2, max_length=120)
    total_score: int = Field(..., ge=1, le=100)
    risk_score: int = Field(..., ge=1, le=100)
    saturation_estimate: str = Field(..., min_length=3, max_length=120)
    content_expansion_score: int = Field(..., ge=1, le=100)
    reasoning: str = Field(..., min_length=10, max_length=800)

    @field_validator("niche_name", "saturation_estimate", "reasoning")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Opportunity score text fields cannot be blank.")
        return cleaned


class OpportunityRanking(BaseModel):
    """Structured output wrapper for a ranked niche list."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    opportunities: list[OpportunityScore] = Field(..., min_length=1, max_length=30)

    @model_validator(mode="after")
    def sort_by_total_score(self) -> OpportunityRanking:
        self.opportunities.sort(key=lambda item: item.total_score, reverse=True)
        return self


def _system_prompt() -> str:
    return """
You are a senior KDP opportunity analyst for children's activity workbooks.

Rank multiple workbook niche ideas against each other using practical publishing judgment.

Score each niche:
- total_score: overall publishing opportunity from 1 to 100.
- risk_score: higher means riskier because of competition, trend dependence, weak differentiation, or content limits.
- saturation_estimate: Low, Medium, High, or Very High with a short qualifier.
- content_expansion_score: ability to expand into series, bundles, worksheets, printables, classroom packs, and seasonal versions.

Consider demand, competition, monetization, expansion potential, and cross-platform potential.
Avoid recommending niches based on copyrighted characters, trademarked worlds, or branded styles.
Return the opportunities sorted from strongest to weakest.
""".strip()


def _user_prompt(niches: list[str]) -> str:
    niche_lines = "\n".join(f"- {niche}" for niche in niches)
    return f"""
Rank these children's activity workbook niche ideas:

{niche_lines}

Be direct and comparative. Explain why each niche scores where it does.
""".strip()


def rank_opportunities(niches: list[str]) -> list[OpportunityScore]:
    """Rank multiple workbook niches using structured OpenAI output."""
    cleaned = [niche.strip() for niche in niches if niche.strip()]
    if len(cleaned) < 2:
        raise ValueError("Enter at least two niche ideas to compare.")
    if len(set(cleaned)) != len(cleaned):
        raise ValueError("Niche ideas must be unique.")

    client = get_openai_client()
    settings = get_settings()
    system_prompt = _system_prompt()
    user_prompt = _user_prompt(cleaned)

    responses_api = getattr(client, "responses", None)
    if responses_api is not None and hasattr(responses_api, "parse"):
        response = responses_api.parse(
            model=settings.model_text_planner,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=OpportunityRanking,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise RuntimeError("OpenAI returned no parsed opportunity ranking.")
        return parsed.opportunities

    completion = client.beta.chat.completions.parse(
        model=settings.model_text_planner,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=OpportunityRanking,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("OpenAI returned no parsed opportunity ranking.")
    return parsed.opportunities


def _slugify(text: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "_" for character in text).strip("_")
    return slug or "opportunity_ranking"


def save_opportunity_scores(scores: list[OpportunityScore], output_dir: Path | None = None) -> Path:
    """Save opportunity ranking as CSV under outputs/research."""
    target_dir = output_dir or (get_settings().outputs_dir / "research")
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    leading_name = _slugify(scores[0].niche_name if scores else "opportunities")
    output_path = target_dir / f"{timestamp}_{leading_name}_opportunities.csv"

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "rank",
                "niche_name",
                "total_score",
                "risk_score",
                "saturation_estimate",
                "content_expansion_score",
                "reasoning",
            ],
        )
        writer.writeheader()
        for rank, score in enumerate(scores, start=1):
            writer.writerow(
                {
                    "rank": rank,
                    "niche_name": score.niche_name,
                    "total_score": score.total_score,
                    "risk_score": score.risk_score,
                    "saturation_estimate": score.saturation_estimate,
                    "content_expansion_score": score.content_expansion_score,
                    "reasoning": score.reasoning,
                }
            )

    return output_path
