from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.config import get_settings


def slugify_project_name(name: str) -> str:
    """Create a folder-safe project name."""
    slug = "".join(character.lower() if character.isalnum() else "_" for character in name).strip("_")
    return slug or "activity_book_project"


def current_project_dir() -> Path:
    """Return the active working project directory."""
    path = get_settings().outputs_dir / "current_project"
    path.mkdir(parents=True, exist_ok=True)
    return path


def saved_projects_dir() -> Path:
    """Return the saved projects directory."""
    path = get_settings().outputs_dir / "projects"
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_saved_projects() -> list[str]:
    """List saved project folder names."""
    return sorted(path.name for path in saved_projects_dir().iterdir() if path.is_dir())


def save_current_project(project_name: str) -> Path:
    """Copy the active project into outputs/projects."""
    source = current_project_dir()
    destination = saved_projects_dir() / slugify_project_name(project_name)

    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)

    manifest_path = destination / "project_manifest.json"
    manifest_path.write_text(
        json.dumps({"project_name": project_name, "folder": destination.name}, indent=2),
        encoding="utf-8",
    )
    return destination


def load_saved_project(project_slug: str) -> Path:
    """Copy a saved project into outputs/current_project."""
    source = saved_projects_dir() / project_slug
    if not source.exists():
        raise FileNotFoundError(f"Saved project not found: {project_slug}")

    destination = current_project_dir()
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    return destination


def load_sample_project(sample_dir: str | Path) -> Path:
    """Copy a bundled sample into outputs/current_project."""
    source = Path(sample_dir)
    if not source.exists():
        raise FileNotFoundError(f"Sample project not found: {source}")

    destination = current_project_dir()
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    return destination
