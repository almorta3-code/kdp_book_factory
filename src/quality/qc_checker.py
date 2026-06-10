from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from PIL import Image
from reportlab.lib.units import inch

from src.layout.pdf_builder import SAFE_MARGIN
from src.schemas.book import AnimalUnit, BookBlueprint, BookRequest


QCStatus = Literal["pass", "warning", "fail"]

COPYRIGHTED_CHARACTER_NAMES = {
    "mickey",
    "minnie",
    "elsa",
    "anna",
    "moana",
    "simba",
    "pikachu",
    "spongebob",
    "harry potter",
    "spider-man",
    "batman",
    "superman",
    "barbie",
    "winnie",
}

TRADEMARKED_STYLE_NAMES = {
    "disney",
    "pixar",
    "marvel",
    "dc comics",
    "pokemon",
    "studio ghibli",
    "nintendo",
    "lego",
    "dreamworks",
    "barbie",
}

ANSWER_KEY_REQUIRED_TYPES = {
    "word_search",
    "maze",
    "dot_to_dot",
    "matching",
    "quiz",
}


@dataclass(frozen=True)
class QCItem:
    """One quality-control finding."""

    check: str
    status: QCStatus
    message: str


def _safe_asset_name(text: str) -> str:
    return "".join(character.lower() if character.isalnum() else "_" for character in text).strip("_")


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


def _contains_forbidden_term(text: str, terms: set[str]) -> str | None:
    lowered = text.lower()
    for term in terms:
        if term in lowered:
            return term
    return None


def _status_counts(items: list[QCItem]) -> dict[str, int]:
    return {
        "pass": sum(1 for item in items if item.status == "pass"),
        "warning": sum(1 for item in items if item.status == "warning"),
        "fail": sum(1 for item in items if item.status == "fail"),
    }


def _check_page_count(blueprint: BookBlueprint, request: BookRequest | None) -> QCItem:
    planned_pages = len(blueprint.page_plan)
    if request is None:
        return QCItem("Page count matches request", "warning", f"No request.json found; blueprint has {planned_pages} planned pages.")
    if planned_pages == request.page_count:
        return QCItem("Page count matches request", "pass", f"Blueprint has {planned_pages} planned pages.")
    return QCItem(
        "Page count matches request",
        "fail",
        f"Request asks for {request.page_count} pages, but blueprint has {planned_pages}.",
    )


def _expected_asset_paths(content_units: list[AnimalUnit], assets_dir: Path) -> list[Path]:
    paths = [assets_dir / "cover.png"]
    for index, unit in enumerate(content_units, start=1):
        safe_name = _safe_asset_name(unit.animal_name)
        prefix = f"{index:02d}_{safe_name}"
        paths.extend(
            [
                assets_dir / f"{prefix}_character.png",
                assets_dir / f"{prefix}_coloring.png",
                assets_dir / f"{prefix}_icon.png",
            ]
        )
    return paths


def _check_missing_images(content_units: list[AnimalUnit], assets_dir: Path) -> QCItem:
    missing = [path.name for path in _expected_asset_paths(content_units, assets_dir) if not path.exists()]
    if not missing:
        return QCItem("No missing images", "pass", "All expected cover, character, coloring, and icon images exist.")
    return QCItem("No missing images", "fail", f"Missing image assets: {', '.join(missing[:12])}.")


def _check_image_resolution(content_units: list[AnimalUnit], assets_dir: Path) -> QCItem:
    low_resolution: list[str] = []
    unreadable: list[str] = []
    for path in _expected_asset_paths(content_units, assets_dir):
        if not path.exists():
            continue
        try:
            with Image.open(path) as image:
                width, height = image.size
        except Exception:
            unreadable.append(path.name)
            continue
        if width < 900 or height < 900:
            low_resolution.append(f"{path.name} ({width}x{height})")

    if unreadable:
        return QCItem("Image resolution is acceptable", "fail", f"Unreadable image files: {', '.join(unreadable)}.")
    if low_resolution:
        return QCItem("Image resolution is acceptable", "warning", f"Low-resolution images: {', '.join(low_resolution[:8])}.")
    return QCItem("Image resolution is acceptable", "pass", "Existing images are at least 900px on each side.")


def _check_answer_keys(blueprint: BookBlueprint, activity_data: dict[str, Any] | list[dict[str, Any]] | None) -> QCItem:
    lookup = _activity_lookup(activity_data)
    missing: list[str] = []
    for page in blueprint.page_plan:
        page_type = page.page_type
        if page_type not in ANSWER_KEY_REQUIRED_TYPES:
            continue
        data = lookup.get(page.page_number, {})
        has_answer_key = bool(page.answer_key) or bool(data.get("answer_key"))
        if not has_answer_key:
            missing.append(f"page {page.page_number} {page.title}")

    if not missing:
        return QCItem("No missing answer keys", "pass", "All answer-key-required activity pages have answer data.")
    return QCItem("No missing answer keys", "fail", f"Missing answer keys: {', '.join(missing[:10])}.")


def _check_duplicate_units(content_units: list[AnimalUnit]) -> QCItem:
    names = [unit.animal_name.strip().lower() for unit in content_units]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if not duplicates:
        return QCItem("No duplicate animal units", "pass", "Animal/topic unit names are unique.")
    return QCItem("No duplicate animal units", "fail", f"Duplicate units: {', '.join(duplicates)}.")


def _check_facts_simple(content_units: list[AnimalUnit]) -> QCItem:
    complex_facts: list[str] = []
    for unit in content_units:
        for fact in unit.fun_facts:
            words = fact.split()
            average_word_length = sum(len(word.strip(".,;:!?")) for word in words) / max(len(words), 1)
            if len(words) > 20 or average_word_length > 8:
                complex_facts.append(f"{unit.animal_name}: {fact}")

    if not complex_facts:
        return QCItem("Facts are simple and age appropriate", "pass", "Facts are short and use simple wording by heuristic checks.")
    return QCItem(
        "Facts are simple and age appropriate",
        "warning",
        f"Some facts may be too complex: {' | '.join(complex_facts[:5])}.",
    )


def _check_forbidden_terms(blueprint: BookBlueprint, content_units: list[AnimalUnit], terms: set[str], label: str) -> QCItem:
    text_parts = [
        blueprint.title,
        blueprint.subtitle,
        blueprint.promise,
        blueprint.unique_angle,
        blueprint.visual_style,
        blueprint.kdp_positioning,
    ]
    for unit in content_units:
        text_parts.extend(
            [
                unit.animal_name,
                unit.short_story,
                unit.coloring_page_prompt,
                unit.flashcard_text,
                *unit.fun_facts,
                *unit.image_prompts,
            ]
        )

    combined = "\n".join(text_parts)
    forbidden = _contains_forbidden_term(combined, terms)
    if forbidden is None:
        return QCItem(label, "pass", "No known restricted names found in generated text.")
    return QCItem(label, "fail", f"Found restricted term: {forbidden}.")


def _check_safe_margins() -> QCItem:
    if SAFE_MARGIN >= 0.25 * inch:
        return QCItem("Margins are safe", "pass", f"PDF safe margin is {SAFE_MARGIN / inch:.2f} inches.")
    return QCItem("Margins are safe", "fail", f"PDF safe margin is only {SAFE_MARGIN / inch:.2f} inches.")


def _check_word_search_answers(activity_data: dict[str, Any] | list[dict[str, Any]] | None) -> QCItem:
    lookup = _activity_lookup(activity_data)
    checked = 0
    failures: list[str] = []
    for page_number, data in lookup.items():
        if data.get("activity_type") != "word_search":
            continue
        checked += 1
        words = data.get("words", [])
        answer_key = data.get("answer_key", {})
        for word in words:
            if word not in answer_key or not answer_key[word].get("cells"):
                failures.append(f"page {page_number}: {word}")

    if failures:
        return QCItem("Word search answers exist", "fail", f"Missing word-search answers: {', '.join(failures[:10])}.")
    if checked == 0:
        return QCItem("Word search answers exist", "warning", "No generated word-search activity data found to inspect.")
    return QCItem("Word search answers exist", "pass", f"Checked {checked} word-search activity payloads.")


def _check_quiz_answers(activity_data: dict[str, Any] | list[dict[str, Any]] | None) -> QCItem:
    lookup = _activity_lookup(activity_data)
    checked = 0
    failures: list[str] = []
    for page_number, data in lookup.items():
        if data.get("activity_type") != "quiz":
            continue
        checked += 1
        answer_key = data.get("answer_key", {})
        for question in data.get("questions", []):
            option_ids = {option.get("id") for option in question.get("options", [])}
            correct_id = answer_key.get(question.get("id"))
            if correct_id not in option_ids:
                failures.append(f"page {page_number}: {question.get('id')}")

    if failures:
        return QCItem("Quiz answers are valid", "fail", f"Invalid quiz answers: {', '.join(failures[:10])}.")
    if checked == 0:
        return QCItem("Quiz answers are valid", "warning", "No generated quiz activity data found to inspect.")
    return QCItem("Quiz answers are valid", "pass", f"Checked {checked} quiz activity payloads.")


def _check_pdf_exists(pdf_path: Path) -> QCItem:
    if not pdf_path.exists():
        return QCItem("PDF exists and is not empty", "fail", f"Missing PDF: {pdf_path.as_posix()}.")
    size = pdf_path.stat().st_size
    if size <= 1024:
        return QCItem("PDF exists and is not empty", "fail", f"PDF exists but is too small: {size} bytes.")
    return QCItem("PDF exists and is not empty", "pass", f"PDF exists with size {size} bytes.")


def render_qc_report_markdown(items: list[QCItem]) -> str:
    """Build a markdown QC report for the current project."""
    counts = _status_counts(items)
    lines = [
        "# Quality Control Report",
        "",
        f"Summary: {counts['pass']} pass, {counts['warning']} warning, {counts['fail']} fail",
        "",
        "| Status | Check | Result |",
        "| --- | --- | --- |",
    ]
    for item in items:
        lines.append(f"| {item.status.upper()} | {item.check} | {item.message.replace('|', '/')} |")
    lines.append("")
    return "\n".join(lines)


def run_quality_checks(
    blueprint: BookBlueprint,
    content_units: list[AnimalUnit],
    project_dir: str | Path,
    request: BookRequest | None = None,
    activity_data: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> tuple[list[QCItem], Path]:
    """Run project QC checks and write outputs/current_project/qc_report.md."""
    project_path = Path(project_dir)
    assets_dir = project_path / "assets"
    pdf_path = project_path / "interior.pdf"

    items = [
        _check_page_count(blueprint, request),
        _check_missing_images(content_units, assets_dir),
        _check_answer_keys(blueprint, activity_data),
        _check_duplicate_units(content_units),
        _check_facts_simple(content_units),
        _check_forbidden_terms(blueprint, content_units, COPYRIGHTED_CHARACTER_NAMES, "No copyrighted character names"),
        _check_forbidden_terms(blueprint, content_units, TRADEMARKED_STYLE_NAMES, "No trademarked style names"),
        _check_safe_margins(),
        _check_image_resolution(content_units, assets_dir),
        _check_word_search_answers(activity_data),
        _check_quiz_answers(activity_data),
        _check_pdf_exists(pdf_path),
    ]

    report_path = project_path / "qc_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_qc_report_markdown(items), encoding="utf-8")
    return items, report_path
