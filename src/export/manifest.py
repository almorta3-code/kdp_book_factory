from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path


def build_output_manifest(output_path: Path) -> dict[str, str]:
    """Create basic metadata for a generated artifact."""
    return {
        "output_path": output_path.as_posix(),
        "created_at": datetime.now(UTC).isoformat(),
    }
