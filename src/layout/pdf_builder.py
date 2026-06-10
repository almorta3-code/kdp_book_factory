from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

from src.compliance.provenance_engine import record_output_file, update_project_provenance
from src.schemas.book import AnimalUnit, BookBlueprint, ContentUnitBatch


PAGE_WIDTH, PAGE_HEIGHT = letter
SAFE_MARGIN = 0.5 * inch
INNER_MARGIN = 0.32 * inch
PASTEL_BLUE = colors.HexColor("#BFE7F5")
PASTEL_GREEN = colors.HexColor("#CDECCB")
PASTEL_YELLOW = colors.HexColor("#FFF1A8")
PASTEL_PINK = colors.HexColor("#F8C7D8")
DARK_INK = colors.HexColor("#243746")
LIGHT_INK = colors.HexColor("#5D7180")


TITLE_STYLE = ParagraphStyle(
    "Title",
    fontName="Helvetica-Bold",
    fontSize=30,
    leading=36,
    textColor=DARK_INK,
    alignment=1,
)
SUBTITLE_STYLE = ParagraphStyle(
    "Subtitle",
    fontName="Helvetica",
    fontSize=15,
    leading=20,
    textColor=LIGHT_INK,
    alignment=1,
)
HEADING_STYLE = ParagraphStyle(
    "Heading",
    fontName="Helvetica-Bold",
    fontSize=20,
    leading=24,
    textColor=DARK_INK,
)
BODY_STYLE = ParagraphStyle(
    "Body",
    fontName="Helvetica",
    fontSize=12,
    leading=16,
    textColor=DARK_INK,
)
SMALL_STYLE = ParagraphStyle(
    "Small",
    fontName="Helvetica",
    fontSize=10,
    leading=13,
    textColor=LIGHT_INK,
)


def _as_blueprint(blueprint: BookBlueprint | dict[str, Any]) -> BookBlueprint:
    if isinstance(blueprint, BookBlueprint):
        return blueprint
    return BookBlueprint.model_validate(blueprint)


def _as_units(content_units: list[AnimalUnit] | list[dict[str, Any]] | ContentUnitBatch) -> list[AnimalUnit]:
    if isinstance(content_units, ContentUnitBatch):
        return content_units.units
    return [unit if isinstance(unit, AnimalUnit) else AnimalUnit.model_validate(unit) for unit in content_units]


def _activity_lookup(activity_data: dict[str, Any] | list[dict[str, Any]] | None) -> dict[int, dict[str, Any]]:
    if activity_data is None:
        return {}
    if isinstance(activity_data, dict):
        if "pages" in activity_data and isinstance(activity_data["pages"], list):
            return _activity_lookup(activity_data["pages"])
        if "pages" in activity_data and isinstance(activity_data["pages"], dict):
            return _activity_lookup(activity_data["pages"])
        return {
            int(key): value
            for key, value in activity_data.items()
            if str(key).isdigit() and isinstance(value, dict)
        }
    return {
        int(item["page_number"]): item
        for item in activity_data
        if "page_number" in item
    }


def _safe_asset_name(text: str) -> str:
    return "".join(character.lower() if character.isalnum() else "_" for character in text).strip("_")


def _paragraph(canvas: Canvas, text: str, x: float, y: float, width: float, style: ParagraphStyle) -> float:
    paragraph = Paragraph(escape(text).replace("\n", "<br/>"), style)
    _, height = paragraph.wrap(width, PAGE_HEIGHT)
    paragraph.drawOn(canvas, x, y - height)
    return y - height


def _page_frame(canvas: Canvas, title: str | None = None, page_number: int | None = None) -> None:
    canvas.setStrokeColor(PASTEL_BLUE)
    canvas.setLineWidth(4)
    canvas.roundRect(SAFE_MARGIN / 2, SAFE_MARGIN / 2, PAGE_WIDTH - SAFE_MARGIN, PAGE_HEIGHT - SAFE_MARGIN, 18)

    canvas.setFillColor(PASTEL_YELLOW)
    for x, y in [
        (SAFE_MARGIN, PAGE_HEIGHT - SAFE_MARGIN),
        (PAGE_WIDTH - SAFE_MARGIN, PAGE_HEIGHT - SAFE_MARGIN),
        (SAFE_MARGIN, SAFE_MARGIN),
        (PAGE_WIDTH - SAFE_MARGIN, SAFE_MARGIN),
    ]:
        canvas.circle(x, y, 8, stroke=0, fill=1)

    if title:
        canvas.setFillColor(DARK_INK)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(SAFE_MARGIN, PAGE_HEIGHT - 0.34 * inch, title[:58])
    if page_number is not None:
        canvas.setFillColor(LIGHT_INK)
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(PAGE_WIDTH / 2, 0.28 * inch, str(page_number))


def _rounded_box(canvas: Canvas, x: float, y: float, width: float, height: float, fill_color=colors.white) -> None:
    canvas.setFillColor(fill_color)
    canvas.setStrokeColor(PASTEL_BLUE)
    canvas.setLineWidth(1.4)
    canvas.roundRect(x, y, width, height, 12, stroke=1, fill=1)


def _draw_small_icon(canvas: Canvas, x: float, y: float, fill_color=PASTEL_PINK) -> None:
    canvas.setFillColor(fill_color)
    canvas.setStrokeColor(DARK_INK)
    canvas.setLineWidth(1)
    canvas.circle(x, y, 10, stroke=1, fill=1)
    canvas.circle(x - 4, y + 3, 1.4, stroke=0, fill=1)
    canvas.circle(x + 4, y + 3, 1.4, stroke=0, fill=1)
    canvas.arc(x - 5, y - 5, x + 5, y + 2, 200, 140)


def _draw_image_300dpi(canvas: Canvas, image_path: Path, x: float, y: float, max_width: float, max_height: float) -> bool:
    if not image_path.exists():
        return False

    with Image.open(image_path) as image:
        pixel_width, pixel_height = image.size

    natural_width = pixel_width / 300 * inch
    natural_height = pixel_height / 300 * inch
    scale = min(max_width / natural_width, max_height / natural_height, 1.0)
    draw_width = natural_width * scale
    draw_height = natural_height * scale
    canvas.drawImage(
        str(image_path),
        x + (max_width - draw_width) / 2,
        y + (max_height - draw_height) / 2,
        width=draw_width,
        height=draw_height,
        preserveAspectRatio=True,
        mask="auto",
    )
    return True


def _asset_paths_for_unit(unit: AnimalUnit, unit_index: int, assets_dir: Path) -> dict[str, Path]:
    safe_name = _safe_asset_name(unit.animal_name)
    prefix = f"{unit_index:02d}_{safe_name}"
    return {
        "character": assets_dir / f"{prefix}_character.png",
        "coloring": assets_dir / f"{prefix}_coloring.png",
        "icon": assets_dir / f"{prefix}_icon.png",
    }


def _draw_title_page(canvas: Canvas, blueprint: BookBlueprint, assets_dir: Path) -> None:
    _page_frame(canvas)
    _paragraph(canvas, blueprint.title, SAFE_MARGIN, PAGE_HEIGHT - 1.55 * inch, PAGE_WIDTH - 2 * SAFE_MARGIN, TITLE_STYLE)
    _paragraph(canvas, blueprint.subtitle, SAFE_MARGIN, PAGE_HEIGHT - 2.45 * inch, PAGE_WIDTH - 2 * SAFE_MARGIN, SUBTITLE_STYLE)

    _rounded_box(canvas, 1.2 * inch, 3.0 * inch, PAGE_WIDTH - 2.4 * inch, 3.25 * inch, colors.HexColor("#F7FCFF"))
    cover_path = assets_dir / "cover.png"
    if not _draw_image_300dpi(canvas, cover_path, 1.45 * inch, 3.2 * inch, PAGE_WIDTH - 2.9 * inch, 2.85 * inch):
        canvas.setFillColor(PASTEL_GREEN)
        canvas.circle(PAGE_WIDTH / 2, 4.65 * inch, 75, stroke=0, fill=1)

    _paragraph(canvas, blueprint.promise, 1.1 * inch, 2.05 * inch, PAGE_WIDTH - 2.2 * inch, BODY_STYLE)
    _draw_small_icon(canvas, 1.0 * inch, 1.0 * inch, PASTEL_PINK)
    _draw_small_icon(canvas, PAGE_WIDTH - 1.0 * inch, 1.0 * inch, PASTEL_GREEN)
    canvas.showPage()


def _draw_story_page(canvas: Canvas, unit: AnimalUnit, unit_index: int, assets_dir: Path, page_number: int) -> None:
    _page_frame(canvas, unit.animal_name, page_number)
    _paragraph(canvas, unit.animal_name, SAFE_MARGIN, PAGE_HEIGHT - 0.92 * inch, PAGE_WIDTH - 2 * SAFE_MARGIN, HEADING_STYLE)

    assets = _asset_paths_for_unit(unit, unit_index, assets_dir)
    _rounded_box(canvas, 0.75 * inch, 5.75 * inch, 3.0 * inch, 3.0 * inch, colors.white)
    _draw_image_300dpi(canvas, assets["character"], 0.9 * inch, 5.9 * inch, 2.7 * inch, 2.7 * inch)

    _rounded_box(canvas, 4.0 * inch, 5.75 * inch, 3.75 * inch, 3.0 * inch, colors.HexColor("#FFFDF2"))
    _paragraph(canvas, unit.short_story, 4.25 * inch, 8.35 * inch, 3.25 * inch, BODY_STYLE)

    _rounded_box(canvas, 0.75 * inch, 1.05 * inch, PAGE_WIDTH - 1.5 * inch, 4.25 * inch, colors.HexColor("#F7FCFF"))
    y = 4.95 * inch
    y = _paragraph(canvas, "Try These Words", 1.0 * inch, y, 3.0 * inch, HEADING_STYLE) - 0.12 * inch
    for word in unit.vocabulary_words[:8]:
        canvas.setFillColor(DARK_INK)
        canvas.setFont("Helvetica", 14)
        canvas.drawString(1.15 * inch, y, word)
        y -= 0.35 * inch
    canvas.showPage()


def _draw_flashcard_page(canvas: Canvas, unit: AnimalUnit, page_number: int) -> None:
    _page_frame(canvas, f"{unit.animal_name} Facts", page_number)
    _paragraph(canvas, f"{unit.animal_name} Flashcard", SAFE_MARGIN, PAGE_HEIGHT - 0.92 * inch, PAGE_WIDTH - 2 * SAFE_MARGIN, HEADING_STYLE)

    _rounded_box(canvas, 0.85 * inch, 5.7 * inch, PAGE_WIDTH - 1.7 * inch, 2.3 * inch, colors.HexColor("#FFFDF2"))
    _paragraph(canvas, unit.flashcard_text, 1.1 * inch, 7.55 * inch, PAGE_WIDTH - 2.2 * inch, BODY_STYLE)

    _rounded_box(canvas, 0.85 * inch, 1.0 * inch, PAGE_WIDTH - 1.7 * inch, 4.25 * inch, colors.white)
    y = 4.88 * inch
    for fact in unit.fun_facts[:5]:
        _draw_small_icon(canvas, 1.13 * inch, y + 0.05 * inch, PASTEL_GREEN)
        y = _paragraph(canvas, fact, 1.45 * inch, y + 0.16 * inch, PAGE_WIDTH - 2.45 * inch, BODY_STYLE) - 0.18 * inch
    canvas.showPage()


def _draw_word_search(canvas: Canvas, data: dict[str, Any], x: float, y: float, size: float) -> None:
    grid = data.get("grid", [])
    if not grid:
        return
    rows = len(grid)
    cell = size / rows
    canvas.setStrokeColor(DARK_INK)
    canvas.setFont("Helvetica-Bold", min(14, cell * 0.45))
    for row_index, row in enumerate(grid):
        for col_index, letter in enumerate(row):
            cell_x = x + col_index * cell
            cell_y = y + size - (row_index + 1) * cell
            canvas.rect(cell_x, cell_y, cell, cell, stroke=1, fill=0)
            canvas.drawCentredString(cell_x + cell / 2, cell_y + cell * 0.32, letter)


def _draw_maze(canvas: Canvas, data: dict[str, Any], x: float, y: float, width: float, height: float) -> None:
    maze_width = max(1, int(data.get("width", 1)))
    maze_height = max(1, int(data.get("height", 1)))
    scale_x = width / maze_width
    scale_y = height / maze_height
    canvas.setStrokeColor(DARK_INK)
    canvas.setLineWidth(1.5)
    for wall in data.get("wall_coordinates", []):
        canvas.line(
            x + wall["x1"] * scale_x,
            y + height - wall["y1"] * scale_y,
            x + wall["x2"] * scale_x,
            y + height - wall["y2"] * scale_y,
        )


def _draw_dot_to_dot(canvas: Canvas, data: dict[str, Any], x: float, y: float, width: float, height: float) -> None:
    source_width = float(data.get("canvas", {}).get("width", 700))
    source_height = float(data.get("canvas", {}).get("height", 900))
    canvas.setStrokeColor(DARK_INK)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 8)
    for point in data.get("points", []):
        point_x = x + float(point["x"]) / source_width * width
        point_y = y + height - float(point["y"]) / source_height * height
        canvas.circle(point_x, point_y, 4, stroke=1, fill=1)
        canvas.drawString(point_x + 5, point_y + 3, str(point["label"]))


def _draw_matching(canvas: Canvas, data: dict[str, Any], x: float, y: float, width: float, height: float) -> None:
    left = data.get("left_column", [])
    right = data.get("right_column", [])
    count = max(len(left), len(right), 1)
    step = height / count
    canvas.setFont("Helvetica", 11)
    for index, item in enumerate(left):
        item_y = y + height - (index + 0.7) * step
        canvas.drawString(x, item_y, item["text"][:28])
        canvas.circle(x + width * 0.42, item_y + 3, 3, stroke=1, fill=0)
    for index, item in enumerate(right):
        item_y = y + height - (index + 0.7) * step
        canvas.circle(x + width * 0.58, item_y + 3, 3, stroke=1, fill=0)
        canvas.drawString(x + width * 0.62, item_y, item["text"][:28])


def _draw_tracing(canvas: Canvas, data: dict[str, Any], x: float, y: float, width: float, height: float) -> None:
    canvas.setStrokeColor(LIGHT_INK)
    canvas.setDash(4, 4)
    for line in data.get("text_lines", [])[:8]:
        line_y = y + height - (float(line.get("y", 120)) / 900 * height)
        canvas.setFont("Helvetica", min(44, int(line.get("font_size", 42))))
        canvas.drawString(x + 0.25 * inch, line_y, str(line.get("text", ""))[:18])
        canvas.line(x + 0.25 * inch, line_y - 8, x + width - 0.25 * inch, line_y - 8)
    canvas.setDash()


def _draw_quiz(canvas: Canvas, data: dict[str, Any], x: float, y: float, width: float, height: float) -> None:
    cursor_y = y + height - 0.2 * inch
    for item in data.get("questions", [])[:4]:
        cursor_y = _paragraph(canvas, item["question"], x, cursor_y, width, BODY_STYLE) - 0.05 * inch
        for option in item.get("options", []):
            canvas.setFont("Helvetica", 10)
            canvas.circle(x + 0.1 * inch, cursor_y - 0.03 * inch, 4, stroke=1, fill=0)
            canvas.drawString(x + 0.25 * inch, cursor_y - 0.08 * inch, f"{option['id']}. {option['text']}"[:70])
            cursor_y -= 0.24 * inch
        cursor_y -= 0.08 * inch


def _draw_activity_payload(canvas: Canvas, data: dict[str, Any], x: float, y: float, width: float, height: float) -> None:
    activity_type = data.get("activity_type")
    if activity_type == "word_search":
        _draw_word_search(canvas, data, x + 0.4 * inch, y + 0.35 * inch, min(width - 0.8 * inch, height - 0.7 * inch))
    elif activity_type == "maze":
        _draw_maze(canvas, data, x + 0.35 * inch, y + 0.35 * inch, width - 0.7 * inch, height - 0.7 * inch)
    elif activity_type == "dot_to_dot":
        _draw_dot_to_dot(canvas, data, x + 0.35 * inch, y + 0.35 * inch, width - 0.7 * inch, height - 0.7 * inch)
    elif activity_type == "matching":
        _draw_matching(canvas, data, x + 0.35 * inch, y + 0.35 * inch, width - 0.7 * inch, height - 0.7 * inch)
    elif activity_type == "tracing":
        _draw_tracing(canvas, data, x + 0.35 * inch, y + 0.35 * inch, width - 0.7 * inch, height - 0.7 * inch)
    elif activity_type == "quiz":
        _draw_quiz(canvas, data, x + 0.35 * inch, y + 0.35 * inch, width - 0.7 * inch, height - 0.7 * inch)
    else:
        canvas.setFont("Helvetica", 14)
        canvas.setFillColor(LIGHT_INK)
        canvas.drawCentredString(x + width / 2, y + height / 2, "Activity space")


def _draw_activity_page(canvas: Canvas, title: str, data: dict[str, Any], page_number: int) -> None:
    _page_frame(canvas, title, page_number)
    _paragraph(canvas, title, SAFE_MARGIN, PAGE_HEIGHT - 0.9 * inch, PAGE_WIDTH - 2 * SAFE_MARGIN, HEADING_STYLE)
    _rounded_box(canvas, 0.75 * inch, 1.0 * inch, PAGE_WIDTH - 1.5 * inch, 8.2 * inch, colors.white)
    _draw_activity_payload(canvas, data, 0.95 * inch, 1.18 * inch, PAGE_WIDTH - 1.9 * inch, 7.75 * inch)
    canvas.showPage()


def _draw_coloring_page(canvas: Canvas, unit: AnimalUnit, unit_index: int, assets_dir: Path, page_number: int) -> None:
    _page_frame(canvas, f"Color {unit.animal_name}", page_number)
    _paragraph(canvas, f"Color {unit.animal_name}", SAFE_MARGIN, PAGE_HEIGHT - 0.9 * inch, PAGE_WIDTH - 2 * SAFE_MARGIN, HEADING_STYLE)
    _rounded_box(canvas, 0.7 * inch, 1.0 * inch, PAGE_WIDTH - 1.4 * inch, 8.35 * inch, colors.white)
    assets = _asset_paths_for_unit(unit, unit_index, assets_dir)
    _draw_image_300dpi(canvas, assets["coloring"], 0.9 * inch, 1.2 * inch, PAGE_WIDTH - 1.8 * inch, 7.9 * inch)
    canvas.showPage()


def _draw_answer_key_page(canvas: Canvas, answer_items: list[tuple[str, Any]], page_number: int) -> None:
    _page_frame(canvas, "Answer Key", page_number)
    _paragraph(canvas, "Answer Key", SAFE_MARGIN, PAGE_HEIGHT - 0.9 * inch, PAGE_WIDTH - 2 * SAFE_MARGIN, HEADING_STYLE)
    y = PAGE_HEIGHT - 1.35 * inch
    for title, answer in answer_items[:10]:
        _rounded_box(canvas, 0.75 * inch, y - 0.75 * inch, PAGE_WIDTH - 1.5 * inch, 0.62 * inch, colors.HexColor("#F7FCFF"))
        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(DARK_INK)
        canvas.drawString(0.95 * inch, y - 0.32 * inch, title[:36])
        canvas.setFont("Helvetica", 8)
        answer_text = json.dumps(answer)[:180]
        canvas.drawString(3.1 * inch, y - 0.32 * inch, answer_text)
        y -= 0.82 * inch
        if y < 1.0 * inch:
            canvas.showPage()
            _page_frame(canvas, "Answer Key", page_number)
            y = PAGE_HEIGHT - 1.0 * inch
    canvas.showPage()


def _draw_certificate_page(canvas: Canvas, blueprint: BookBlueprint, page_number: int) -> None:
    _page_frame(canvas, "Certificate", page_number)
    _rounded_box(canvas, 0.95 * inch, 2.0 * inch, PAGE_WIDTH - 1.9 * inch, 6.4 * inch, colors.HexColor("#FFFDF2"))
    _paragraph(canvas, "Certificate of Completion", 1.2 * inch, 7.55 * inch, PAGE_WIDTH - 2.4 * inch, TITLE_STYLE)
    _paragraph(canvas, f"This certifies that", 1.2 * inch, 6.3 * inch, PAGE_WIDTH - 2.4 * inch, SUBTITLE_STYLE)
    canvas.setStrokeColor(DARK_INK)
    canvas.line(2.0 * inch, 5.4 * inch, PAGE_WIDTH - 2.0 * inch, 5.4 * inch)
    _paragraph(canvas, f"completed {blueprint.title}", 1.2 * inch, 4.55 * inch, PAGE_WIDTH - 2.4 * inch, SUBTITLE_STYLE)
    _draw_small_icon(canvas, 1.45 * inch, 2.55 * inch, PASTEL_PINK)
    _draw_small_icon(canvas, PAGE_WIDTH - 1.45 * inch, 2.55 * inch, PASTEL_GREEN)
    canvas.showPage()


def build_interior_pdf(
    blueprint: BookBlueprint | dict[str, Any],
    content_units: list[AnimalUnit] | list[dict[str, Any]] | ContentUnitBatch,
    activity_data: dict[str, Any] | list[dict[str, Any]] | None,
    assets_dir: str | Path,
    output_pdf: str | Path,
) -> Path:
    """Build an 8.5 x 11 inch KDP-style workbook interior PDF."""
    parsed_blueprint = _as_blueprint(blueprint)
    parsed_units = _as_units(content_units)
    parsed_activity_data = _activity_lookup(activity_data)
    assets_path = Path(assets_dir)
    output_path = Path(output_pdf)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    canvas = Canvas(str(output_path), pagesize=letter)
    _draw_title_page(canvas, parsed_blueprint, assets_path)

    page_number = 2
    answer_items: list[tuple[str, Any]] = []

    for unit_index, unit in enumerate(parsed_units, start=1):
        _draw_story_page(canvas, unit, unit_index, assets_path, page_number)
        page_number += 1
        _draw_flashcard_page(canvas, unit, page_number)
        page_number += 1
        _draw_coloring_page(canvas, unit, unit_index, assets_path, page_number)
        page_number += 1

    for page_spec in parsed_blueprint.page_plan:
        if page_spec.page_type not in {"maze", "word_search", "dot_to_dot", "matching", "tracing", "counting", "story"}:
            continue
        data = parsed_activity_data.get(page_spec.page_number) or page_spec.activity_data
        if not data:
            data = {"activity_type": page_spec.page_type}
        data.setdefault("activity_type", page_spec.page_type)
        _draw_activity_page(canvas, page_spec.title, data, page_number)
        if page_spec.answer_key:
            answer_items.append((page_spec.title, page_spec.answer_key))
        if isinstance(data, dict) and data.get("answer_key"):
            answer_items.append((page_spec.title, data["answer_key"]))
        page_number += 1

    if answer_items:
        _draw_answer_key_page(canvas, answer_items, page_number)
        page_number += 1

    _draw_certificate_page(canvas, parsed_blueprint, page_number)
    canvas.save()
    try:
        record_output_file(output_path)
        update_project_provenance(book_title=parsed_blueprint.title, generation_event="Built interior PDF", output_file=output_path)
    except Exception:
        pass
    return output_path


class PdfBuilder:
    """Thin class wrapper for callers that prefer an object interface."""

    def build(
        self,
        blueprint: BookBlueprint | dict[str, Any],
        content_units: list[AnimalUnit] | list[dict[str, Any]] | ContentUnitBatch,
        activity_data: dict[str, Any] | list[dict[str, Any]] | None,
        assets_dir: str | Path,
        output_pdf: str | Path,
    ) -> Path:
        return build_interior_pdf(blueprint, content_units, activity_data, assets_dir, output_pdf)
