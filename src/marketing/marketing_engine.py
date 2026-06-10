from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.branding.brand_builder import BrandProfile
from src.config import get_settings
from src.openai_client import get_openai_client
from src.schemas.book import BookBlueprint


MARKETING_DIR = Path(__file__).resolve().parents[2] / "outputs" / "marketing"


class AmazonMarketingAssets(BaseModel):
    """Amazon listing and A+ content assets."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    title: str = Field(..., min_length=3, max_length=200)
    subtitle: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=80, max_length=5000)
    backend_keywords: list[str] = Field(..., min_length=7, max_length=7)
    a_plus_content: list[str] = Field(..., min_length=5, max_length=12)


class SEOArticle(BaseModel):
    """Blog article draft for organic discovery."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    title: str = Field(..., min_length=8, max_length=160)
    slug: str = Field(..., min_length=3, max_length=120)
    meta_description: str = Field(..., min_length=50, max_length=180)
    target_keyword: str = Field(..., min_length=3, max_length=100)
    outline: list[str] = Field(..., min_length=4, max_length=12)
    draft: str = Field(..., min_length=300, max_length=3000)


class ScriptAsset(BaseModel):
    """Short-form video script for social channels."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    hook: str = Field(..., min_length=5, max_length=160)
    script: str = Field(..., min_length=20, max_length=600)
    call_to_action: str = Field(..., min_length=5, max_length=160)


class EmailAsset(BaseModel):
    """Launch email for parents, teachers, or homeschool buyers."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    subject: str = Field(..., min_length=5, max_length=120)
    preview_text: str = Field(..., min_length=10, max_length=180)
    body: str = Field(..., min_length=120, max_length=2000)


class MarketingAssets(BaseModel):
    """Complete launch marketing pack for a workbook and publishing brand."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    campaign_name: str = Field(..., min_length=3, max_length=160)
    audience_summary: str = Field(..., min_length=30, max_length=1000)
    positioning_angle: str = Field(..., min_length=30, max_length=1000)
    amazon: AmazonMarketingAssets
    blog_articles: list[SEOArticle] = Field(..., min_length=5, max_length=5)
    pinterest_pin_ideas: list[str] = Field(..., min_length=20, max_length=20)
    tiktok_scripts: list[ScriptAsset] = Field(..., min_length=30, max_length=30)
    youtube_shorts_scripts: list[ScriptAsset] = Field(..., min_length=30, max_length=30)
    facebook_post_ideas: list[str] = Field(..., min_length=20, max_length=20)
    email_launch_sequence: list[EmailAsset] = Field(..., min_length=5, max_length=10)

    @field_validator("campaign_name", "audience_summary", "positioning_angle")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Marketing text fields cannot be blank.")
        return cleaned

    @field_validator("pinterest_pin_ideas", "facebook_post_ideas")
    @classmethod
    def strip_list_items(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("Marketing lists cannot contain blank values.")
        return cleaned


def _system_prompt() -> str:
    return """
You are a children's publishing launch strategist.

Create complete marketing assets for a KDP activity workbook and its publishing brand.

Rules:
- Write for parents, teachers, homeschool buyers, and gift buyers.
- Keep claims honest and age appropriate.
- Avoid copyrighted characters, trademarked styles, celebrity names, and unsafe platform claims.
- Do not promise medical, developmental, or academic outcomes.
- Make every asset specific to the book hook, audience, and brand.
- Use clean HTML-safe formatting in the Amazon description only.
""".strip()


def _user_prompt(blueprint: BookBlueprint, brand: BrandProfile) -> str:
    topics = ", ".join(blueprint.animal_or_topic_list)
    return f"""
Generate a complete MarketingAssets package.

Book title: {blueprint.title}
Book subtitle: {blueprint.subtitle}
Audience: {blueprint.audience}
Promise: {blueprint.promise}
Unique angle: {blueprint.unique_angle}
Topics: {topics}
KDP positioning: {blueprint.kdp_positioning}

Brand name: {brand.brand_name}
Brand slogan: {brand.slogan}
Visual identity: {brand.visual_identity}
Mascot concept: {brand.mascot_concept}
Publishing strategy: {brand.publishing_strategy}
Future series: {", ".join(brand.future_series)}

Required output:
- Amazon title, subtitle, description, exactly 7 backend keywords, and A+ content modules.
- Exactly 5 SEO blog articles.
- Exactly 20 Pinterest pin ideas.
- Exactly 30 TikTok scripts.
- Exactly 30 YouTube Shorts scripts.
- Exactly 20 Facebook post ideas.
- A practical email launch sequence.
""".strip()


def generate_marketing_assets(blueprint: BookBlueprint, brand: BrandProfile) -> MarketingAssets:
    """Generate a structured marketing asset pack from a book blueprint and brand profile."""
    client = get_openai_client()
    system_prompt = _system_prompt()
    user_prompt = _user_prompt(blueprint, brand)

    responses_api = getattr(client, "responses", None)
    if responses_api is not None and hasattr(responses_api, "parse"):
        response = responses_api.parse(
            model=get_settings().model_text_planner,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=MarketingAssets,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise RuntimeError("OpenAI returned no parsed MarketingAssets.")
        return parsed

    completion = client.beta.chat.completions.parse(
        model=get_settings().model_text_planner,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=MarketingAssets,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("OpenAI returned no parsed MarketingAssets.")
    return parsed


def _slugify(text: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "_" for character in text).strip("_")
    return slug or "marketing_assets"


def _write_text_summary(assets: MarketingAssets, output_path: Path) -> None:
    lines = [
        assets.campaign_name,
        "",
        "Audience",
        assets.audience_summary,
        "",
        "Positioning",
        assets.positioning_angle,
        "",
        "Amazon",
        assets.amazon.title,
        assets.amazon.subtitle,
        assets.amazon.description,
        "",
        "Backend Keywords",
        "\n".join(assets.amazon.backend_keywords),
        "",
        "A+ Content",
        "\n".join(f"- {item}" for item in assets.amazon.a_plus_content),
        "",
        "Pinterest Pin Ideas",
        "\n".join(f"- {item}" for item in assets.pinterest_pin_ideas),
        "",
        "Facebook Post Ideas",
        "\n".join(f"- {item}" for item in assets.facebook_post_ideas),
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def export_marketing_assets(
    blueprint: BookBlueprint,
    brand: BrandProfile,
    output_dir: str | Path | None = None,
) -> dict[str, Path]:
    """Generate and save complete marketing assets under outputs/marketing."""
    target_dir = Path(output_dir) if output_dir is not None else MARKETING_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    assets = generate_marketing_assets(blueprint, brand)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    slug = _slugify(assets.campaign_name)
    json_path = target_dir / f"{timestamp}_{slug}.json"
    txt_path = target_dir / f"{timestamp}_{slug}_summary.txt"

    json_path.write_text(assets.model_dump_json(indent=2), encoding="utf-8")
    _write_text_summary(assets, txt_path)
    return {"json_path": json_path, "summary_path": txt_path, "marketing_dir": target_dir}
