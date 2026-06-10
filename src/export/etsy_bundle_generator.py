from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

from src.schemas.book import AnimalUnit, BookBlueprint


TITLE_STYLE = ParagraphStyle("Title", fontName="Helvetica-Bold", fontSize=24, leading=30, alignment=1)
BODY_STYLE = ParagraphStyle("Body", fontName="Helvetica", fontSize=12, leading=16)


def _paragraph(canvas: Canvas, text: str, x: float, y: float, width: float, style: ParagraphStyle) -> float:
    paragraph = Paragraph(text.replace("\n", "<br/>"), style)
    _, height = paragraph.wrap(width, 11 * inch)
    paragraph.drawOn(canvas, x, y - height)
    return y - height


def _page_frame(canvas: Canvas, title: str) -> None:
    canvas.setStrokeColor(colors.HexColor("#9CC9D8"))
    canvas.setLineWidth(3)
    canvas.roundRect(0.4 * inch, 0.4 * inch, 7.7 * inch, 10.2 * inch, 14)
    _paragraph(canvas, title, 0.75 * inch, 10.1 * inch, 7.0 * inch, TITLE_STYLE)


def _slugify(text: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "_" for character in text).strip("_")
    return slug or "etsy_bundle"


def _write_flashcards(path: Path, units: list[AnimalUnit]) -> None:
    canvas = Canvas(str(path), pagesize=letter)
    for unit in units:
        _page_frame(canvas, f"{unit.animal_name} Flashcard")
        _paragraph(canvas, unit.flashcard_text, 1.0 * inch, 8.7 * inch, 6.5 * inch, BODY_STYLE)
        y = 7.4 * inch
        for fact in unit.fun_facts[:3]:
            canvas.setFont("Helvetica", 12)
            canvas.drawString(1.1 * inch, y, f"- {fact}")
            y -= 0.35 * inch
        canvas.showPage()
    canvas.save()


def _write_posters(path: Path, units: list[AnimalUnit]) -> None:
    canvas = Canvas(str(path), pagesize=letter)
    for unit in units:
        _page_frame(canvas, unit.animal_name)
        canvas.setFont("Helvetica-Bold", 18)
        canvas.drawCentredString(4.25 * inch, 8.3 * inch, unit.habitat[:70])
        _paragraph(canvas, unit.short_story, 1.0 * inch, 6.9 * inch, 6.5 * inch, BODY_STYLE)
        canvas.showPage()
    canvas.save()


def _write_reward_chart(path: Path, blueprint: BookBlueprint) -> None:
    canvas = Canvas(str(path), pagesize=letter)
    _page_frame(canvas, "Reward Chart")
    _paragraph(canvas, f"Great job working on {blueprint.title}!", 1.0 * inch, 9.0 * inch, 6.5 * inch, BODY_STYLE)
    canvas.setFont("Helvetica-Bold", 11)
    for row in range(8):
        y = 7.8 * inch - row * 0.55 * inch
        canvas.drawString(1.0 * inch, y, f"Task {row + 1}")
        for col in range(5):
            canvas.rect(2.4 * inch + col * 0.75 * inch, y - 0.1 * inch, 0.35 * inch, 0.35 * inch)
    canvas.showPage()
    canvas.save()


def _write_certificates(path: Path, blueprint: BookBlueprint) -> None:
    canvas = Canvas(str(path), pagesize=letter)
    _page_frame(canvas, "Certificate of Completion")
    _paragraph(canvas, "This certificate is proudly presented to", 1.0 * inch, 8.0 * inch, 6.5 * inch, BODY_STYLE)
    canvas.line(1.5 * inch, 6.9 * inch, 7.0 * inch, 6.9 * inch)
    _paragraph(canvas, f"for completing {blueprint.title}", 1.0 * inch, 6.2 * inch, 6.5 * inch, BODY_STYLE)
    canvas.showPage()
    canvas.save()


def _write_worksheet_pack(path: Path, units: list[AnimalUnit]) -> None:
    canvas = Canvas(str(path), pagesize=letter)
    for unit in units:
        _page_frame(canvas, f"{unit.animal_name} Worksheet")
        y = 8.8 * inch
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawString(1.0 * inch, y, "Trace these words:")
        y -= 0.45 * inch
        canvas.setDash(3, 3)
        for word in unit.tracing_words[:5]:
            canvas.setFont("Helvetica", 28)
            canvas.drawString(1.0 * inch, y, word)
            canvas.line(1.0 * inch, y - 0.1 * inch, 7.2 * inch, y - 0.1 * inch)
            y -= 0.65 * inch
        canvas.setDash()
        canvas.showPage()
    canvas.save()


def _copy_coloring_pages(bundle_dir: Path, assets_dir: Path, units: list[AnimalUnit]) -> list[Path]:
    output_dir = bundle_dir / "printable_coloring_pages"
    output_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for index, unit in enumerate(units, start=1):
        safe_name = _slugify(unit.animal_name)
        source = assets_dir / f"{index:02d}_{safe_name}_coloring.png"
        destination = output_dir / f"{index:02d}_{safe_name}_coloring.png"
        if source.exists():
            shutil.copy2(source, destination)
            copied.append(destination)
    return copied


def generate_etsy_listing(blueprint: BookBlueprint, units: list[AnimalUnit]) -> dict[str, object]:
    """Generate Etsy listing title, description, and tags locally from project content."""
    topic_words = [unit.animal_name for unit in units[:4]]
    title = f"{blueprint.title} Printable Activity Bundle"
    description = f"""
Printable activity bundle for {blueprint.audience}.

Includes flashcards, posters, reward chart, certificates, worksheet pages, and printable coloring pages.

Theme: {blueprint.title}
Activities: vocabulary practice, tracing, facts, coloring, and reward tracking.

This is a digital printable product. No physical item is shipped.
""".strip()
    tags = [
        "kids printable",
        "activity bundle",
        "homeschool",
        "classroom printable",
        "coloring pages",
        "flashcards",
        "reward chart",
        "worksheet pack",
        *[_slugify(topic).replace("_", " ")[:20] for topic in topic_words],
    ][:13]
    return {"title": title, "description": description, "tags": tags}


def export_etsy_bundle(
    blueprint: BookBlueprint,
    content_units: list[AnimalUnit],
    project_dir: str | Path,
) -> dict[str, Path]:
    """Create Etsy printable products and zip package."""
    project_path = Path(project_dir)
    bundle_dir = project_path / "etsy_bundle"
    assets_dir = project_path / "assets"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    _write_flashcards(bundle_dir / "flashcards.pdf", content_units)
    _write_posters(bundle_dir / "posters.pdf", content_units)
    _write_reward_chart(bundle_dir / "reward_chart.pdf", blueprint)
    _write_certificates(bundle_dir / "certificates.pdf", blueprint)
    _write_worksheet_pack(bundle_dir / "worksheet_pack.pdf", content_units)
    _copy_coloring_pages(bundle_dir, assets_dir, content_units)

    listing = generate_etsy_listing(blueprint, content_units)
    (bundle_dir / "etsy_title.txt").write_text(str(listing["title"]) + "\n", encoding="utf-8")
    (bundle_dir / "etsy_description.txt").write_text(str(listing["description"]) + "\n", encoding="utf-8")
    (bundle_dir / "etsy_tags.txt").write_text("\n".join(listing["tags"]) + "\n", encoding="utf-8")

    zip_path = project_path / "etsy_bundle.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in bundle_dir.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(bundle_dir.parent))

    return {"bundle_dir": bundle_dir, "zip_path": zip_path}
