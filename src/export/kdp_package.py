from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas

from src.compliance.provenance_engine import export_compliance_package, record_output_file, record_prompt, update_project_provenance
from src.config import get_settings
from src.openai_client import get_openai_client
from src.schemas.book import AnimalUnit, BookBlueprint, KDPMetadata


def _build_metadata_system_prompt() -> str:
    """Define listing strategist rules for structured KDP metadata."""
    return """
You are a KDP listing strategist for original children's educational activity books.

Create clean, commercially useful metadata that is honest, age appropriate, and free of copyrighted or trademarked references.

Rules:
- Description must be HTML-safe and use only simple tags such as <p>, <br>, <ul>, <li>, and <b>.
- Include exactly 7 keyword phrases.
- Include exactly 2 category suggestions.
- Backend search terms should be practical search phrases, not spam.
- Launch checklist should include concrete upload, proofing, and listing checks.
- Do not claim affiliation with Amazon, KDP, schools, brands, celebrities, or copyrighted characters.
""".strip()


def _build_metadata_user_prompt(blueprint: BookBlueprint, content_units: list[AnimalUnit]) -> str:
    """Create the metadata generation brief from project data."""
    topics = ", ".join(blueprint.animal_or_topic_list)
    unit_names = ", ".join(unit.animal_name for unit in content_units)

    return f"""
Create KDPMetadata for this children's activity book.

Title concept: {blueprint.title}
Subtitle concept: {blueprint.subtitle}
Audience: {blueprint.audience}
Promise: {blueprint.promise}
Unique angle: {blueprint.unique_angle}
KDP positioning: {blueprint.kdp_positioning}
Core topics: {topics}
Generated content units: {unit_names}

Return a polished listing package with an HTML-safe description, exactly 7 keyword phrases, exactly 2 category suggestions, backend search terms, and a launch checklist.
""".strip()


def generate_kdp_metadata(blueprint: BookBlueprint, content_units: list[AnimalUnit]) -> KDPMetadata:
    """Generate KDP listing metadata using OpenAI structured output."""
    settings = get_settings()
    client = get_openai_client()
    system_prompt = _build_metadata_system_prompt()
    user_prompt = _build_metadata_user_prompt(blueprint, content_units)

    responses_api = getattr(client, "responses", None)
    if responses_api is not None and hasattr(responses_api, "parse"):
        response = responses_api.parse(
            model=settings.model_text_fast,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=KDPMetadata,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise RuntimeError("OpenAI returned no parsed KDPMetadata.")
        try:
            record_prompt(
                "kdp_metadata_generator",
                settings.model_text_fast,
                f"{system_prompt}\n\n{user_prompt}",
                f"Generated KDP metadata for {parsed.title}",
            )
            update_project_provenance(
                book_title=parsed.title,
                model_used=settings.model_text_fast,
                generation_event="Generated KDP metadata",
            )
        except Exception:
            pass
        return parsed

    completion = client.beta.chat.completions.parse(
        model=settings.model_text_fast,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=KDPMetadata,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("OpenAI returned no parsed KDPMetadata.")
    try:
        record_prompt(
            "kdp_metadata_generator",
            settings.model_text_fast,
            f"{system_prompt}\n\n{user_prompt}",
            f"Generated KDP metadata for {parsed.title}",
        )
        update_project_provenance(
            book_title=parsed.title,
            model_used=settings.model_text_fast,
            generation_event="Generated KDP metadata",
        )
    except Exception:
        pass
    return parsed


def _write_text(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def _cover_prompt(blueprint: BookBlueprint) -> str:
    return f"""
Create an original children's KDP activity book cover image.

Book concept: {blueprint.title}
Subtitle direction: {blueprint.subtitle}
Audience: {blueprint.audience}
Hook: {blueprint.unique_angle}
Visual style: {blueprint.visual_style}

Do not put readable text in the image. Leave clean open areas for title and subtitle to be added later in layout software.
Use a cheerful, kid-friendly, original composition with no copyrighted characters or trademarked styles.
""".strip()


def _amazon_listing(metadata: KDPMetadata) -> str:
    return f"""
TITLE
{metadata.title}

SUBTITLE
{metadata.subtitle}

AUTHOR
{metadata.author_name_placeholder}

DESCRIPTION
{metadata.description}

KEYWORDS
{chr(10).join(metadata.keywords)}

CATEGORY SUGGESTIONS
{chr(10).join(metadata.categories)}

BACKEND SEARCH TERMS
{", ".join(metadata.backend_search_terms)}

LAUNCH CHECKLIST
{chr(10).join(f"- {item}" for item in metadata.launch_checklist)}
""".strip()


def _social_posts(metadata: KDPMetadata, blueprint: BookBlueprint) -> str:
    return f"""
Post 1:
New screen-free activity fun for kids: {metadata.title}. A playful workbook built around {blueprint.unique_angle.lower()}

Post 2:
Looking for a creative workbook with puzzles, coloring, and learning moments? {metadata.title} is designed for {blueprint.audience.lower()}

Post 3:
Make quiet time more creative with {metadata.title}: activities, facts, and kid-friendly pages in one printable-style workbook.
""".strip()


def _etsy_description(metadata: KDPMetadata) -> str:
    return f"""
{metadata.title}

{metadata.subtitle}

{metadata.description}

Great for:
- Screen-free quiet time
- Homeschool activities
- Early learning practice
- Giftable activity book ideas

Keywords:
{", ".join(metadata.keywords)}
""".strip()


def _create_cover_pdf_placeholder(path: Path, metadata: KDPMetadata) -> None:
    canvas = Canvas(str(path), pagesize=letter)
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawCentredString(4.25 * inch, 9.2 * inch, "Cover PDF Placeholder")
    canvas.setFont("Helvetica", 11)
    canvas.drawCentredString(4.25 * inch, 8.8 * inch, "Use KDP Cover Calculator for final wrap dimensions.")
    canvas.rect(1.0 * inch, 1.2 * inch, 6.5 * inch, 7.0 * inch)
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawCentredString(4.25 * inch, 6.6 * inch, metadata.title[:56])
    canvas.setFont("Helvetica", 10)
    canvas.drawCentredString(4.25 * inch, 6.25 * inch, metadata.subtitle[:76])
    canvas.showPage()
    canvas.save()


def _create_interior_pdf_placeholder(path: Path, metadata: KDPMetadata) -> None:
    canvas = Canvas(str(path), pagesize=letter)
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawCentredString(4.25 * inch, 9.2 * inch, "Interior PDF Placeholder")
    canvas.setFont("Helvetica", 11)
    canvas.drawCentredString(4.25 * inch, 8.8 * inch, "Export the full interior before uploading to KDP.")
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawCentredString(4.25 * inch, 7.8 * inch, metadata.title[:64])
    canvas.showPage()
    canvas.save()


def _copy_or_placeholder(source: Path, destination: Path, placeholder_text: str) -> None:
    if source.exists():
        shutil.copy2(source, destination)
    else:
        _write_text(destination, placeholder_text)


def _copy_or_create_cover_png(source: Path, destination: Path) -> None:
    if source.exists():
        shutil.copy2(source, destination)
        return

    image = Image.new("RGBA", (1800, 2700), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((120, 120, 1680, 2580), outline=(80, 120, 150, 255), width=14)
    draw.ellipse((520, 620, 1280, 1380), outline=(120, 170, 190, 255), width=18)
    draw.arc((690, 830, 820, 960), 10, 170, fill=(60, 90, 110, 255), width=10)
    draw.arc((980, 830, 1110, 960), 10, 170, fill=(60, 90, 110, 255), width=10)
    draw.arc((720, 980, 1080, 1220), 20, 160, fill=(60, 90, 110, 255), width=12)
    image.save(destination, format="PNG")


def export_kdp_upload_package(
    blueprint: BookBlueprint,
    content_units: list[AnimalUnit],
    project_dir: str | Path,
    metadata: KDPMetadata | None = None,
) -> dict[str, Path]:
    """Create the complete KDP upload package folder and zip archive."""
    project_path = Path(project_dir)
    package_dir = project_path / "kdp_upload_package"
    package_dir.mkdir(parents=True, exist_ok=True)

    assets_dir = project_path / "assets"
    metadata = metadata or generate_kdp_metadata(blueprint, content_units)

    _write_text(package_dir / "cover_prompt.txt", _cover_prompt(blueprint))
    _copy_or_create_cover_png(assets_dir / "cover.png", package_dir / "cover.png")
    _create_cover_pdf_placeholder(package_dir / "cover.pdf", metadata)
    interior_source = project_path / "interior.pdf"
    if interior_source.exists():
        shutil.copy2(interior_source, package_dir / "interior.pdf")
    else:
        _create_interior_pdf_placeholder(package_dir / "interior.pdf", metadata)

    (package_dir / "metadata.json").write_text(
        metadata.model_dump_json(indent=2),
        encoding="utf-8",
    )
    _write_text(package_dir / "amazon_listing.txt", _amazon_listing(metadata))
    _write_text(package_dir / "keywords.txt", "\n".join(metadata.keywords))
    _write_text(package_dir / "categories.txt", "\n".join(metadata.categories))
    _write_text(package_dir / "social_posts.txt", _social_posts(metadata, blueprint))
    _write_text(package_dir / "etsy_description.txt", _etsy_description(metadata))
    try:
        for file_path in package_dir.iterdir():
            if file_path.is_file():
                record_output_file(file_path, project_path)
        export_compliance_package(project_path, package_dir / "compliance")
    except Exception:
        pass

    zip_path = project_path / "kdp_upload_package.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in package_dir.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(package_dir.parent))
    try:
        record_output_file(zip_path, project_path)
        update_project_provenance(book_title=metadata.title, generation_event="Exported KDP upload package", output_file=zip_path)
    except Exception:
        pass

    return {
        "package_dir": package_dir,
        "zip_path": zip_path,
        "metadata_path": package_dir / "metadata.json",
    }
