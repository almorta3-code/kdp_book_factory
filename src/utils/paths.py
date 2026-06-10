from __future__ import annotations

from pathlib import Path

from src.config import get_settings


def get_output_path(filename: str) -> Path:
    """Return a path inside the configured outputs directory."""
    return get_settings().outputs_dir / filename
