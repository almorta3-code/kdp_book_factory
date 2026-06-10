from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from src.config import PROJECT_ROOT, get_settings


class DashboardMetric(BaseModel):
    """One headline dashboard metric."""

    model_config = ConfigDict(extra="forbid", strict=True)

    label: str
    value: int


class DashboardRow(BaseModel):
    """Simple row used by Streamlit tables and charts."""

    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    category: str
    path: str
    updated_at: str


class DashboardData(BaseModel):
    """Aggregated local publishing activity."""

    model_config = ConfigDict(extra="forbid", strict=True)

    metrics: list[DashboardMetric] = Field(default_factory=list)
    project_rows: list[DashboardRow] = Field(default_factory=list)
    brand_rows: list[DashboardRow] = Field(default_factory=list)
    book_rows: list[DashboardRow] = Field(default_factory=list)
    language_rows: list[DashboardRow] = Field(default_factory=list)
    export_rows: list[DashboardRow] = Field(default_factory=list)
    chart_rows: list[dict[str, int | str]] = Field(default_factory=list)


def _safe_updated_at(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except OSError:
        return ""


def _row(path: Path, category: str, root: Path) -> DashboardRow:
    try:
        relative_path = path.relative_to(root).as_posix()
    except ValueError:
        relative_path = path.as_posix()
    return DashboardRow(
        name=path.stem if path.is_file() else path.name,
        category=category,
        path=relative_path,
        updated_at=_safe_updated_at(path),
    )


def _dirs(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted([item for item in path.iterdir() if item.is_dir()], key=lambda item: item.name.lower())


def _files(path: Path, pattern: str) -> list[Path]:
    if not path.exists():
        return []
    return sorted(path.rglob(pattern), key=lambda item: item.as_posix().lower())


def _project_has_book(project_dir: Path) -> bool:
    book_markers = [
        "blueprint.json",
        "content_units.json",
        "interior.pdf",
        "kdp_upload_package.zip",
    ]
    return any((project_dir / marker).exists() for marker in book_markers)


def _collect_projects(outputs_dir: Path) -> list[Path]:
    projects_dir = outputs_dir / "projects"
    projects = _dirs(projects_dir)
    current_project = outputs_dir / "current_project"
    if current_project.exists():
        projects.insert(0, current_project)
    return projects


def _collect_exports(outputs_dir: Path) -> list[Path]:
    export_patterns = [
        "kdp_upload_package.zip",
        "etsy_bundle.zip",
        "teacher_pack.zip",
        "homeschool_pack.zip",
        "interior.pdf",
        "cover.pdf",
    ]
    exports: list[Path] = []
    for pattern in export_patterns:
        exports.extend(_files(outputs_dir, pattern))
    return sorted(set(exports), key=lambda path: path.as_posix().lower())


def collect_dashboard_data() -> DashboardData:
    """Scan local files and return publishing dashboard data."""
    outputs_dir = get_settings().outputs_dir
    brands_dir = PROJECT_ROOT / "projects" / "brands"
    root = PROJECT_ROOT

    project_paths = _collect_projects(outputs_dir)
    brand_paths = _files(brands_dir, "*.json")
    research_paths = _files(outputs_dir / "research", "*.json") + _files(outputs_dir / "research", "*.csv")
    language_paths = _files(outputs_dir, "language_packs/*.json")
    export_paths = _collect_exports(outputs_dir)

    book_paths = [path for path in project_paths if _project_has_book(path)]

    project_rows = [_row(path, "Project", root) for path in project_paths]
    brand_rows = [_row(path, "Brand", root) for path in brand_paths]
    book_rows = [_row(path, "Book", root) for path in book_paths]
    language_rows = [_row(path, "Language Pack", root) for path in language_paths]
    export_rows = [_row(path, "Export", root) for path in export_paths]

    metrics = [
        DashboardMetric(label="Books Created", value=len(book_paths)),
        DashboardMetric(label="Niches Researched", value=len(research_paths)),
        DashboardMetric(label="Brands Created", value=len(brand_paths)),
        DashboardMetric(label="Export Count", value=len(export_paths)),
    ]

    chart_counter = Counter(
        {
            "Projects": len(project_paths),
            "Brands": len(brand_paths),
            "Books": len(book_paths),
            "Languages": len(language_paths),
            "Exports": len(export_paths),
            "Research": len(research_paths),
        }
    )
    chart_rows = [{"category": category, "count": count} for category, count in chart_counter.items()]

    return DashboardData(
        metrics=metrics,
        project_rows=project_rows,
        brand_rows=brand_rows,
        book_rows=book_rows,
        language_rows=language_rows,
        export_rows=export_rows,
        chart_rows=chart_rows,
    )
