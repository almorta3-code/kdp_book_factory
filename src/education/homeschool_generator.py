from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from pydantic import BaseModel, ConfigDict, Field, field_validator
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

from src.config import get_settings
from src.openai_client import get_openai_client
from src.schemas.book import BookBlueprint


class HomeschoolPack(BaseModel):
    """Home-learning product plan derived from a workbook blueprint."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    title: str = Field(..., min_length=3, max_length=160)
    age_range: str = Field(..., min_length=2, max_length=50)
    weekly_plans: list[str] = Field(..., min_length=2, max_length=8)
    learning_objectives: list[str] = Field(..., min_length=3, max_length=12)
    daily_activities: list[str] = Field(..., min_length=5, max_length=30)
    parent_guide: list[str] = Field(..., min_length=3, max_length=15)
    progress_tracker: list[str] = Field(..., min_length=4, max_length=20)
    supply_list: list[str] = Field(..., min_length=3, max_length=20)
    extension_ideas: list[str] = Field(..., min_length=3, max_length=15)
    product_positioning: str = Field(..., min_length=30, max_length=1200)

    @field_validator("title", "age_range", "product_positioning")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Homeschool pack text fields cannot be blank.")
        return cleaned

    @field_validator(
        "weekly_plans",
        "learning_objectives",
        "daily_activities",
        "parent_guide",
        "progress_tracker",
        "supply_list",
        "extension_ideas",
    )
    @classmethod
    def strip_list_items(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("Homeschool pack lists cannot contain blank values.")
        return cleaned


def _system_prompt() -> str:
    return """
You are a homeschool curriculum product designer.

Convert a children's activity workbook blueprint into a practical homeschool product.

Rules:
- Target parents teaching children in the K-5 range.
- Keep the plan simple, flexible, and realistic for home use.
- Use short daily sessions and low-prep activities.
- Include clear learning objectives and a parent-friendly progress tracker.
- Avoid copyrighted characters, trademarked styles, and brand references.
""".strip()


def _user_prompt(blueprint: BookBlueprint) -> str:
    page_titles = ", ".join(page.title for page in blueprint.page_plan[:24])
    return f"""
Create a HomeschoolPack for this workbook blueprint.

Title: {blueprint.title}
Subtitle: {blueprint.subtitle}
Audience: {blueprint.audience}
Promise: {blueprint.promise}
Unique angle: {blueprint.unique_angle}
Topics: {", ".join(blueprint.animal_or_topic_list)}
Representative pages: {page_titles}

Generate weekly plans, learning objectives, daily activities, parent guide, progress tracker, supply list,
extension ideas, and product positioning for selling this as a homeschool printable product.
""".strip()


def generate_homeschool_pack(blueprint: BookBlueprint) -> HomeschoolPack:
    """Generate structured homeschool resources from a book blueprint."""
    client = get_openai_client()
    system_prompt = _system_prompt()
    user_prompt = _user_prompt(blueprint)

    responses_api = getattr(client, "responses", None)
    if responses_api is not None and hasattr(responses_api, "parse"):
        response = responses_api.parse(
            model=get_settings().model_text_fast,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=HomeschoolPack,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise RuntimeError("OpenAI returned no parsed HomeschoolPack.")
        return parsed

    completion = client.beta.chat.completions.parse(
        model=get_settings().model_text_fast,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=HomeschoolPack,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("OpenAI returned no parsed HomeschoolPack.")
    return parsed


TITLE_STYLE = ParagraphStyle("Title", fontName="Helvetica-Bold", fontSize=22, leading=28, alignment=1)
HEADING_STYLE = ParagraphStyle("Heading", fontName="Helvetica-Bold", fontSize=15, leading=19)
BODY_STYLE = ParagraphStyle("Body", fontName="Helvetica", fontSize=10.5, leading=14)


def _paragraph(canvas: Canvas, text: str, x: float, y: float, width: float, style: ParagraphStyle) -> float:
    paragraph = Paragraph(escape(text).replace("\n", "<br/>"), style)
    _, height = paragraph.wrap(width, 11 * inch)
    paragraph.drawOn(canvas, x, y - height)
    return y - height


def _new_page(canvas: Canvas, title: str) -> float:
    canvas.setStrokeColorRGB(0.72, 0.61, 0.82)
    canvas.setLineWidth(2)
    canvas.roundRect(0.45 * inch, 0.45 * inch, 7.6 * inch, 10.1 * inch, 12)
    return _paragraph(canvas, title, 0.75 * inch, 10.2 * inch, 7.0 * inch, TITLE_STYLE) - 0.35 * inch


def _write_section(canvas: Canvas, title: str, items: list[str], y: float) -> float:
    y = _paragraph(canvas, title, 0.8 * inch, y, 6.9 * inch, HEADING_STYLE) - 0.08 * inch
    for item in items:
        y = _paragraph(canvas, f"- {item}", 0.95 * inch, y, 6.6 * inch, BODY_STYLE) - 0.05 * inch
        if y < 0.9 * inch:
            canvas.showPage()
            y = _new_page(canvas, title)
    return y - 0.15 * inch


def _write_text_section(canvas: Canvas, title: str, text: str, y: float) -> float:
    y = _paragraph(canvas, title, 0.8 * inch, y, 6.9 * inch, HEADING_STYLE) - 0.12 * inch
    words = text.split()
    chunks: list[str] = []
    chunk: list[str] = []
    for word in words:
        chunk.append(word)
        if len(" ".join(chunk)) >= 260:
            chunks.append(" ".join(chunk))
            chunk = []
    if chunk:
        chunks.append(" ".join(chunk))

    for chunk_text in chunks:
        if y < 1.4 * inch:
            canvas.showPage()
            y = _new_page(canvas, title)
        y = _paragraph(canvas, chunk_text, 0.95 * inch, y, 6.6 * inch, BODY_STYLE) - 0.1 * inch
    return y


def render_homeschool_pack_pdf(pack: HomeschoolPack, output_pdf: str | Path) -> Path:
    """Render a HomeschoolPack as homeschool_pack.pdf."""
    output_path = Path(output_pdf)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    canvas = Canvas(str(output_path), pagesize=letter)
    y = _new_page(canvas, pack.title)
    y = _paragraph(canvas, f"Age Range: {pack.age_range}", 0.8 * inch, y, 6.9 * inch, BODY_STYLE) - 0.2 * inch
    y = _write_section(canvas, "Weekly Plans", pack.weekly_plans, y)
    y = _write_section(canvas, "Learning Objectives", pack.learning_objectives, y)
    y = _write_section(canvas, "Daily Activities", pack.daily_activities, y)
    y = _write_section(canvas, "Parent Guide", pack.parent_guide, y)
    y = _write_section(canvas, "Progress Tracker", pack.progress_tracker, y)
    y = _write_section(canvas, "Supply List", pack.supply_list, y)
    y = _write_section(canvas, "Extension Ideas", pack.extension_ideas, y)
    _write_text_section(canvas, "Product Positioning", pack.product_positioning, y)
    canvas.showPage()
    canvas.save()
    return output_path


def export_homeschool_pack(blueprint: BookBlueprint, project_dir: str | Path) -> dict[str, Path]:
    """Generate and export homeschool_pack.pdf, structured JSON, and a zip package."""
    project_path = Path(project_dir)
    output_dir = project_path / "homeschool_pack"
    output_dir.mkdir(parents=True, exist_ok=True)

    pack = generate_homeschool_pack(blueprint)
    json_path = output_dir / "homeschool_pack.json"
    json_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")
    pdf_path = render_homeschool_pack_pdf(pack, output_dir / "homeschool_pack.pdf")

    zip_path = project_path / "homeschool_pack.zip"
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
        for file_path in output_dir.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(project_path))

    return {"json_path": json_path, "pdf_path": pdf_path, "pack_dir": output_dir, "zip_path": zip_path}
