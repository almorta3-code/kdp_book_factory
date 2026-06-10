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
from src.google_client import generate_structured
from src.schemas.book import BookBlueprint


class TeacherPack(BaseModel):
    """Classroom resources derived from a workbook blueprint for grades K-5."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    title: str = Field(..., min_length=3, max_length=160)
    grade_band: str = Field(..., min_length=1, max_length=40)
    learning_objectives: list[str] = Field(..., min_length=3, max_length=12)
    lesson_plans: list[str] = Field(..., min_length=1, max_length=10)
    discussion_questions: list[str] = Field(..., min_length=5, max_length=20)
    worksheets: list[str] = Field(..., min_length=2, max_length=12)
    classroom_activities: list[str] = Field(..., min_length=2, max_length=12)
    assessments: list[str] = Field(..., min_length=2, max_length=12)
    teacher_notes: str = Field(..., min_length=20, max_length=1500)

    @field_validator("title", "grade_band", "teacher_notes")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Teacher pack text fields cannot be blank.")
        return cleaned

    @field_validator(
        "learning_objectives",
        "lesson_plans",
        "discussion_questions",
        "worksheets",
        "classroom_activities",
        "assessments",
    )
    @classmethod
    def strip_list_items(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("Teacher pack lists cannot contain blank values.")
        return cleaned


def _system_prompt() -> str:
    return """
You are an elementary curriculum designer for grades K-5.

Create practical teacher resources that support a children's activity workbook.

Rules:
- Keep activities age appropriate for grades K-5.
- Include flexible lesson plans that can work in classrooms, homeschool, or small groups.
- Worksheets should be printable concepts, not completed worksheet images.
- Assessments should be simple and low-pressure.
- Avoid copyrighted characters, trademarked styles, and brand references.
""".strip()


def _user_prompt(blueprint: BookBlueprint) -> str:
    page_titles = ", ".join(page.title for page in blueprint.page_plan[:20])
    return f"""
Create a TeacherPack for this workbook blueprint.

Title: {blueprint.title}
Subtitle: {blueprint.subtitle}
Audience: {blueprint.audience}
Promise: {blueprint.promise}
Unique angle: {blueprint.unique_angle}
Topics: {", ".join(blueprint.animal_or_topic_list)}
Representative pages: {page_titles}

Target grade range: K-5.

Generate lesson plans, discussion questions, worksheets, classroom activities, assessments, learning objectives, and teacher notes.
""".strip()


def generate_teacher_pack(blueprint: BookBlueprint) -> TeacherPack:
    """Generate structured K-5 teacher resources from a book blueprint."""
    settings = get_settings()
    system_prompt = _system_prompt()
    user_prompt = _user_prompt(blueprint)
    return generate_structured(settings.model_text_fast, system_prompt, user_prompt, TeacherPack)


TITLE_STYLE = ParagraphStyle("Title", fontName="Helvetica-Bold", fontSize=22, leading=28, alignment=1)
HEADING_STYLE = ParagraphStyle("Heading", fontName="Helvetica-Bold", fontSize=15, leading=19)
BODY_STYLE = ParagraphStyle("Body", fontName="Helvetica", fontSize=10.5, leading=14)


def _paragraph(canvas: Canvas, text: str, x: float, y: float, width: float, style: ParagraphStyle) -> float:
    paragraph = Paragraph(escape(text).replace("\n", "<br/>"), style)
    _, height = paragraph.wrap(width, 11 * inch)
    paragraph.drawOn(canvas, x, y - height)
    return y - height


def _new_page(canvas: Canvas, title: str) -> float:
    canvas.setStrokeColorRGB(0.55, 0.72, 0.78)
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
    """Write longer notes in small chunks so they can continue across pages."""
    y = _paragraph(canvas, title, 0.8 * inch, y, 6.9 * inch, HEADING_STYLE) - 0.12 * inch
    words = text.split()
    chunk: list[str] = []
    chunks: list[str] = []
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


def render_teacher_pack_pdf(pack: TeacherPack, output_pdf: str | Path) -> Path:
    """Render a TeacherPack as teacher_pack.pdf."""
    output_path = Path(output_pdf)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    canvas = Canvas(str(output_path), pagesize=letter)
    y = _new_page(canvas, pack.title)
    y = _paragraph(canvas, f"Grade Band: {pack.grade_band}", 0.8 * inch, y, 6.9 * inch, BODY_STYLE) - 0.2 * inch
    y = _write_section(canvas, "Learning Objectives", pack.learning_objectives, y)
    y = _write_section(canvas, "Lesson Plans", pack.lesson_plans, y)
    y = _write_section(canvas, "Discussion Questions", pack.discussion_questions, y)
    y = _write_section(canvas, "Worksheets", pack.worksheets, y)
    y = _write_section(canvas, "Classroom Activities", pack.classroom_activities, y)
    y = _write_section(canvas, "Assessments", pack.assessments, y)
    _write_text_section(canvas, "Teacher Notes", pack.teacher_notes, y)
    canvas.showPage()
    canvas.save()
    return output_path


def export_teacher_pack(blueprint: BookBlueprint, project_dir: str | Path) -> dict[str, Path]:
    """Generate and export teacher_pack.pdf, structured JSON, and a zip package."""
    project_path = Path(project_dir)
    output_dir = project_path / "teacher_pack"
    output_dir.mkdir(parents=True, exist_ok=True)

    pack = generate_teacher_pack(blueprint)
    json_path = output_dir / "teacher_pack.json"
    json_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")
    pdf_path = render_teacher_pack_pdf(pack, output_dir / "teacher_pack.pdf")

    zip_path = project_path / "teacher_pack.zip"
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
        for file_path in output_dir.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(project_path))

    return {"json_path": json_path, "pdf_path": pdf_path, "pack_dir": output_dir, "zip_path": zip_path}
