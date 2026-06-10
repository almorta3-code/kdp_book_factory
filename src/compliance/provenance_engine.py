from __future__ import annotations

import json
import shutil
import uuid
import zipfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from pydantic import BaseModel, ConfigDict, Field, field_validator
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

from src.config import get_settings

if TYPE_CHECKING:
    from src.branding.brand_builder import BrandProfile
    from src.branding.character_engine import CharacterProfile


PROVENANCE_DIR_NAME = "provenance"
COPYRIGHT_TERMS = [
    "disney",
    "pixar",
    "marvel",
    "pokemon",
    "bluey",
    "paw patrol",
    "star wars",
    "harry potter",
    "mickey mouse",
    "minnie mouse",
    "spider-man",
    "frozen",
]
TRADEMARK_TERMS = [
    "lego",
    "barbie",
    "nintendo",
    "minecraft",
    "roblox",
    "sesame street",
    "cocomelon",
    "peppa pig",
    "hot wheels",
    "crayola",
]


class PromptRecord(BaseModel):
    """A prompt sent to an AI model, without any API keys."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    prompt_id: str = Field(..., min_length=8)
    module_name: str = Field(..., min_length=2, max_length=120)
    timestamp: str = Field(..., min_length=10)
    model_used: str = Field(..., min_length=2, max_length=120)
    prompt_text: str = Field(..., min_length=1)
    response_summary: str = Field(..., min_length=1, max_length=1200)


class AssetRecord(BaseModel):
    """A generated asset and the prompt/hash evidence behind it."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    asset_id: str = Field(..., min_length=8)
    asset_type: str = Field(..., min_length=2, max_length=100)
    creation_date: str = Field(..., min_length=10)
    source_prompt: str = Field(..., min_length=1)
    file_path: str = Field(..., min_length=1)
    sha256_hash: str = Field(default="", max_length=64)


class ProjectProvenance(BaseModel):
    """Full project-level provenance record."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    project_id: str
    project_name: str
    creation_timestamp: str
    last_modified_timestamp: str
    creator_name: str
    brand_name: str
    book_title: str
    version: str
    language: str
    models_used: list[str] = Field(default_factory=list)
    generation_summary: list[str] = Field(default_factory=list)
    source_files: list[str] = Field(default_factory=list)
    generated_assets: list[str] = Field(default_factory=list)
    prompts_used: list[str] = Field(default_factory=list)
    output_files: list[str] = Field(default_factory=list)
    file_hashes: dict[str, str] = Field(default_factory=dict)
    compliance_status: str = "pending"

    @field_validator("models_used", "generation_summary", "source_files", "generated_assets", "prompts_used", "output_files")
    @classmethod
    def unique_list(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        return list(dict.fromkeys(cleaned))


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def current_project_path(project_dir: str | Path | None = None) -> Path:
    path = Path(project_dir) if project_dir is not None else get_settings().outputs_dir / "current_project"
    path.mkdir(parents=True, exist_ok=True)
    return path


def provenance_dir(project_dir: str | Path | None = None) -> Path:
    path = current_project_path(project_dir) / PROVENANCE_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _json_path(project_dir: str | Path | None, filename: str) -> Path:
    return provenance_dir(project_dir) / filename


def _load_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _relative(path: str | Path, project_dir: str | Path | None = None) -> str:
    file_path = Path(path)
    base = current_project_path(project_dir)
    try:
        return file_path.relative_to(base).as_posix()
    except ValueError:
        return file_path.as_posix()


def sha256_file(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_project_provenance(project_dir: str | Path | None = None) -> ProjectProvenance:
    path = _json_path(project_dir, "project_provenance.json")
    if path.exists():
        return ProjectProvenance.model_validate_json(path.read_text(encoding="utf-8"))

    timestamp = now_iso()
    project_path = current_project_path(project_dir)
    return ProjectProvenance(
        project_id=str(uuid.uuid4()),
        project_name=project_path.name,
        creation_timestamp=timestamp,
        last_modified_timestamp=timestamp,
        creator_name="KDP Activity Book Factory user",
        brand_name="",
        book_title="",
        version="1.0",
        language="",
        compliance_status="pending",
    )


def save_project_provenance(provenance: ProjectProvenance, project_dir: str | Path | None = None) -> Path:
    provenance.last_modified_timestamp = now_iso()
    path = _json_path(project_dir, "project_provenance.json")
    path.write_text(provenance.model_dump_json(indent=2), encoding="utf-8")
    return path


def update_project_provenance(
    project_dir: str | Path | None = None,
    project_name: str | None = None,
    creator_name: str | None = None,
    brand_name: str | None = None,
    book_title: str | None = None,
    language: str | None = None,
    model_used: str | None = None,
    generation_event: str | None = None,
    source_file: str | Path | None = None,
    output_file: str | Path | None = None,
    compliance_status: str | None = None,
) -> Path:
    provenance = load_project_provenance(project_dir)
    if project_name:
        provenance.project_name = project_name
    if creator_name:
        provenance.creator_name = creator_name
    if brand_name:
        provenance.brand_name = brand_name
    if book_title:
        provenance.book_title = book_title
    if language:
        provenance.language = language
    if model_used:
        provenance.models_used.append(model_used)
    if generation_event:
        provenance.generation_summary.append(generation_event)
    if source_file:
        provenance.source_files.append(_relative(source_file, project_dir))
    if output_file:
        provenance.output_files.append(_relative(output_file, project_dir))
    if compliance_status:
        provenance.compliance_status = compliance_status
    return save_project_provenance(provenance, project_dir)


def record_prompt(
    module_name: str,
    model_used: str,
    prompt_text: str,
    response_summary: str,
    project_dir: str | Path | None = None,
) -> Path:
    record = PromptRecord(
        prompt_id=str(uuid.uuid4()),
        module_name=module_name,
        timestamp=now_iso(),
        model_used=model_used,
        prompt_text=prompt_text,
        response_summary=response_summary,
    )
    path = _json_path(project_dir, "prompt_history.json")
    records = _load_json(path, [])
    assert isinstance(records, list)
    records.append(record.model_dump())
    _write_json(path, records)

    provenance = load_project_provenance(project_dir)
    provenance.prompts_used.append(record.prompt_id)
    provenance.models_used.append(model_used)
    provenance.generation_summary.append(f"{module_name}: {response_summary}")
    save_project_provenance(provenance, project_dir)
    _write_ai_usage_report(project_dir)
    return path


def register_asset(
    asset_type: str,
    source_prompt: str,
    file_path: str | Path,
    project_dir: str | Path | None = None,
) -> Path:
    file_path = Path(file_path)
    digest = sha256_file(file_path) if file_path.exists() and file_path.is_file() else ""
    record = AssetRecord(
        asset_id=str(uuid.uuid4()),
        asset_type=asset_type,
        creation_date=now_iso(),
        source_prompt=source_prompt,
        file_path=_relative(file_path, project_dir),
        sha256_hash=digest,
    )
    path = _json_path(project_dir, "asset_registry.json")
    records = _load_json(path, [])
    assert isinstance(records, list)
    records.append(record.model_dump())
    _write_json(path, records)

    provenance = load_project_provenance(project_dir)
    provenance.generated_assets.append(record.file_path)
    if digest:
        provenance.file_hashes[record.file_path] = digest
    save_project_provenance(provenance, project_dir)
    return path


def record_output_file(file_path: str | Path, project_dir: str | Path | None = None) -> Path:
    file_path = Path(file_path)
    relative = _relative(file_path, project_dir)
    digest = sha256_file(file_path) if file_path.exists() and file_path.is_file() else ""

    provenance = load_project_provenance(project_dir)
    provenance.output_files.append(relative)
    if digest:
        provenance.file_hashes[relative] = digest
    save_project_provenance(provenance, project_dir)
    return hash_project_files(project_dir)


def _hashable_files(project_dir: str | Path | None = None) -> list[Path]:
    project_path = current_project_path(project_dir)
    patterns = ["*.json", "*.pdf", "*.png", "*.txt", "*.csv", "*.zip"]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(project_path.rglob(pattern))
    return sorted(
        [
            file_path
            for file_path in files
            if file_path.is_file()
            and PROVENANCE_DIR_NAME not in file_path.relative_to(project_path).parts
        ],
        key=lambda path: path.as_posix(),
    )


def hash_project_files(project_dir: str | Path | None = None) -> Path:
    hashes = {_relative(file_path, project_dir): sha256_file(file_path) for file_path in _hashable_files(project_dir)}
    path = _json_path(project_dir, "file_hashes.json")
    _write_json(path, hashes)

    provenance = load_project_provenance(project_dir)
    provenance.file_hashes.update(hashes)
    save_project_provenance(provenance, project_dir)
    return path


def register_character(profile: CharacterProfile, project_dir: str | Path | None = None) -> Path:
    path = _json_path(project_dir, "character_registry.json")
    records = _load_json(path, [])
    assert isinstance(records, list)
    records.append(
        {
            "character_name": profile.name,
            "creation_date": now_iso(),
            "prompt": profile.prompt_template,
            "visual_description": f"{profile.species}; {profile.visual_traits}; {profile.clothing}; {profile.accessories}",
            "personality": profile.personality,
        }
    )
    _write_json(path, records)
    update_project_provenance(project_dir, generation_event=f"Registered original character: {profile.name}")
    return path


def register_brand(profile: BrandProfile, project_dir: str | Path | None = None) -> Path:
    path = _json_path(project_dir, "brand_registry.json")
    records = _load_json(path, [])
    assert isinstance(records, list)
    records.append(
        {
            "brand_name": profile.brand_name,
            "slogan": profile.slogan,
            "creation_date": now_iso(),
            "mascot": profile.mascot_concept,
            "visual_identity": profile.visual_identity,
        }
    )
    _write_json(path, records)
    update_project_provenance(
        project_dir,
        brand_name=profile.brand_name,
        generation_event=f"Registered original brand: {profile.brand_name}",
    )
    return path


def _scan_payload(project_dir: str | Path | None, terms: list[str]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    for file_path in _hashable_files(project_dir):
        if file_path.suffix.lower() not in {".json", ".txt", ".csv"}:
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        for term in terms:
            if term in text:
                warnings.append({"term": term, "file": _relative(file_path, project_dir), "message": f"Potential reference: {term}"})
    return warnings


def run_copyright_scan(project_dir: str | Path | None = None) -> list[dict[str, str]]:
    warnings = _scan_payload(project_dir, COPYRIGHT_TERMS)
    _write_json(_json_path(project_dir, "copyright_scan.json"), {"warnings": warnings})
    _refresh_compliance_status(project_dir)
    return warnings


def run_trademark_scan(project_dir: str | Path | None = None) -> list[dict[str, str]]:
    warnings = _scan_payload(project_dir, TRADEMARK_TERMS)
    _write_json(_json_path(project_dir, "trademark_scan.json"), {"warnings": warnings})
    _refresh_compliance_status(project_dir)
    return warnings


def _write_ai_usage_report(project_dir: str | Path | None = None) -> Path:
    prompt_records = _load_json(_json_path(project_dir, "prompt_history.json"), [])
    assert isinstance(prompt_records, list)
    report = {
        "models_used": sorted({record.get("model_used", "") for record in prompt_records if record.get("model_used")}),
        "generation_dates": sorted({record.get("timestamp", "")[:10] for record in prompt_records if record.get("timestamp")}),
        "modules_used": sorted({record.get("module_name", "") for record in prompt_records if record.get("module_name")}),
    }
    path = _json_path(project_dir, "ai_usage_report.json")
    _write_json(path, report)
    return path


def _refresh_compliance_status(project_dir: str | Path | None = None) -> None:
    copyright_warnings = _load_json(_json_path(project_dir, "copyright_scan.json"), {"warnings": []})
    trademark_warnings = _load_json(_json_path(project_dir, "trademark_scan.json"), {"warnings": []})
    has_warnings = bool(copyright_warnings.get("warnings") or trademark_warnings.get("warnings")) if isinstance(copyright_warnings, dict) and isinstance(trademark_warnings, dict) else False
    update_project_provenance(project_dir, compliance_status="warning" if has_warnings else "pass")


TITLE_STYLE = ParagraphStyle("Title", fontName="Helvetica-Bold", fontSize=20, leading=26, alignment=1)
HEADING_STYLE = ParagraphStyle("Heading", fontName="Helvetica-Bold", fontSize=13, leading=17)
BODY_STYLE = ParagraphStyle("Body", fontName="Helvetica", fontSize=9.5, leading=13)


def _paragraph(canvas: Canvas, text: str, x: float, y: float, width: float, style: ParagraphStyle) -> float:
    paragraph = Paragraph(escape(text).replace("\n", "<br/>"), style)
    _, height = paragraph.wrap(width, 11 * inch)
    paragraph.drawOn(canvas, x, y - height)
    return y - height


def _new_page(canvas: Canvas, title: str) -> float:
    canvas.setStrokeColorRGB(0.22, 0.32, 0.42)
    canvas.setLineWidth(1.5)
    canvas.rect(0.5 * inch, 0.5 * inch, 7.5 * inch, 10.0 * inch)
    return _paragraph(canvas, title, 0.8 * inch, 10.15 * inch, 6.9 * inch, TITLE_STYLE) - 0.3 * inch


def _write_section(canvas: Canvas, title: str, lines: list[str], y: float) -> float:
    y = _paragraph(canvas, title, 0.8 * inch, y, 6.9 * inch, HEADING_STYLE) - 0.08 * inch
    for line in lines or ["None recorded."]:
        if y < 0.9 * inch:
            canvas.showPage()
            y = _new_page(canvas, title)
        y = _paragraph(canvas, f"- {line}", 0.95 * inch, y, 6.6 * inch, BODY_STYLE) - 0.04 * inch
    return y - 0.12 * inch


def generate_ownership_report(project_dir: str | Path | None = None) -> Path:
    project_path = current_project_path(project_dir)
    hash_project_files(project_path)
    run_copyright_scan(project_path)
    run_trademark_scan(project_path)
    _write_ai_usage_report(project_path)

    provenance = load_project_provenance(project_path)
    prompt_history = _load_json(_json_path(project_path, "prompt_history.json"), [])
    asset_registry = _load_json(_json_path(project_path, "asset_registry.json"), [])
    character_registry = _load_json(_json_path(project_path, "character_registry.json"), [])
    brand_registry = _load_json(_json_path(project_path, "brand_registry.json"), [])
    file_hashes = _load_json(_json_path(project_path, "file_hashes.json"), {})

    output_path = _json_path(project_path, "ownership_report.pdf")
    canvas = Canvas(str(output_path), pagesize=letter)
    y = _new_page(canvas, "Ownership and Provenance Report")
    y = _write_section(
        canvas,
        "1. Project Information",
        [
            f"Project ID: {provenance.project_id}",
            f"Project Name: {provenance.project_name}",
            f"Book Title: {provenance.book_title or 'Not recorded'}",
            f"Brand Name: {provenance.brand_name or 'Not recorded'}",
            f"Language: {provenance.language or 'Not recorded'}",
            f"Compliance Status: {provenance.compliance_status}",
        ],
        y,
    )
    y = _write_section(canvas, "2. Creation Date", [provenance.creation_timestamp, f"Last modified: {provenance.last_modified_timestamp}"], y)
    y = _write_section(canvas, "3. Models Used", provenance.models_used, y)
    y = _write_section(canvas, "4. Prompt History Summary", [f"{item.get('module_name')}: {item.get('response_summary')}" for item in prompt_history], y)
    y = _write_section(canvas, "5. Generated Assets", [item.get("file_path", "") for item in asset_registry], y)
    y = _write_section(canvas, "6. File Hashes", [f"{name}: {digest}" for name, digest in file_hashes.items()], y)
    y = _write_section(canvas, "7. Character Registry", [item.get("character_name", "") for item in character_registry], y)
    y = _write_section(canvas, "8. Brand Registry", [item.get("brand_name", "") for item in brand_registry], y)
    y = _write_section(canvas, "9. Output Files", provenance.output_files, y)
    _write_section(
        canvas,
        "10. Compliance Declaration",
        [
            "This report records locally generated project evidence from KDP Activity Book Factory.",
            "It documents prompts, generated files, hashes, assets, and registry records available at report time.",
            "The user should still review final files for platform policy, copyright, and trademark compliance before publication.",
        ],
        y,
    )
    canvas.showPage()
    canvas.save()
    record_output_file(output_path, project_path)
    return output_path


def export_compliance_package(project_dir: str | Path | None = None, destination_dir: str | Path | None = None) -> dict[str, Path]:
    project_path = current_project_path(project_dir)
    generate_ownership_report(project_path)
    hash_project_files(project_path)
    _write_ai_usage_report(project_path)

    source_dir = provenance_dir(project_path)
    target_dir = Path(destination_dir) if destination_dir is not None else project_path / "compliance"
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename in [
        "ownership_report.pdf",
        "project_provenance.json",
        "prompt_history.json",
        "asset_registry.json",
        "character_registry.json",
        "brand_registry.json",
        "file_hashes.json",
        "ai_usage_report.json",
        "copyright_scan.json",
        "trademark_scan.json",
    ]:
        source = source_dir / filename
        if source.exists():
            destination = target_dir / ("provenance.json" if filename == "project_provenance.json" else filename)
            shutil.copy2(source, destination)
    result = {"compliance_dir": target_dir, "ownership_report": target_dir / "ownership_report.pdf"}
    if destination_dir is None:
        zip_path = project_path / "compliance_package.zip"
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_path in target_dir.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(target_dir.parent))
        result["zip_path"] = zip_path
    return result
