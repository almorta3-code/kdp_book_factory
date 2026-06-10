from __future__ import annotations

import base64
import time
from pathlib import Path

from PIL import Image, ImageDraw

from src.compliance.provenance_engine import record_prompt, register_asset, update_project_provenance
from src.config import get_settings
from src.openai_client import get_openai_client


STYLE_PREFIX = (
    "Cute educational workbook, soft pastel palette, clean outlines, kid-friendly, "
    "original character design, no copyrighted style, no trademarked characters, "
    "no readable text inside the image"
)


def build_style_prompt(prompt: str, background: str = "clean white background") -> str:
    """Create a consistent safe visual direction for generated workbook assets."""
    cleaned = prompt.strip()
    if not cleaned:
        raise ValueError("Image prompt cannot be blank.")

    return f"{STYLE_PREFIX}, {background}. Subject: {cleaned}."


def _save_placeholder_png(output_path: Path, label: str, prompt: str) -> Path:
    """Create a simple local PNG so the app can run without image API calls."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)

    draw.rectangle((64, 64, 960, 960), outline=(80, 120, 150, 255), width=6)
    draw.ellipse((300, 220, 724, 644), outline=(120, 170, 190, 255), width=8)
    draw.arc((390, 340, 470, 420), 10, 170, fill=(60, 90, 110, 255), width=4)
    draw.arc((554, 340, 634, 420), 10, 170, fill=(60, 90, 110, 255), width=4)
    draw.arc((410, 420, 614, 560), 20, 160, fill=(60, 90, 110, 255), width=5)
    draw.polygon([(220, 770), (512, 650), (804, 770), (512, 850)], outline=(120, 170, 190, 255), fill=None)

    image.save(output_path, format="PNG")
    return output_path


def _extract_image_bytes(response: object) -> bytes:
    """Handle common OpenAI image response shapes without binding to one SDK version."""
    data = getattr(response, "data", None)
    if not data:
        raise RuntimeError("OpenAI image response did not include image data.")

    first_image = data[0]
    b64_json = getattr(first_image, "b64_json", None)
    if b64_json:
        return base64.b64decode(b64_json)

    if isinstance(first_image, dict) and first_image.get("b64_json"):
        return base64.b64decode(first_image["b64_json"])

    raise RuntimeError("OpenAI image response did not include base64 PNG data.")


def _generate_image(
    prompt: str,
    output_path: str | Path,
    asset_type: str,
    background: str,
    placeholder: bool = False,
    retries: int = 2,
) -> Path:
    """Generate exactly one PNG image, with placeholder and retry support."""
    target_path = Path(output_path)
    if target_path.suffix.lower() != ".png":
        target_path = target_path.with_suffix(".png")

    full_prompt = build_style_prompt(prompt, background=background)

    if placeholder:
        output = _save_placeholder_png(target_path, asset_type, full_prompt)
        try:
            register_asset(asset_type, full_prompt, output)
            update_project_provenance(generation_event=f"Created placeholder {asset_type} asset", output_file=output)
        except Exception:
            pass
        return output

    settings = get_settings()
    client = get_openai_client()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = client.images.generate(
                model=settings.model_image,
                prompt=full_prompt,
                size="1024x1024",
                n=1,
                response_format="b64_json",
            )
            target_path.write_bytes(_extract_image_bytes(response))
            try:
                record_prompt("image_generator", settings.model_image, full_prompt, f"Generated {asset_type} image")
                register_asset(asset_type, full_prompt, target_path)
                update_project_provenance(
                    model_used=settings.model_image,
                    generation_event=f"Generated {asset_type} image",
                    output_file=target_path,
                )
            except Exception:
                pass
            return target_path
        except Exception as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(1.5 * (attempt + 1))

    raise RuntimeError(f"Image generation failed after {retries + 1} attempts: {last_error}")


def generate_character_image(prompt: str, output_path: str | Path, placeholder: bool = False) -> Path:
    """Generate one original character image as PNG."""
    return _generate_image(
        prompt,
        output_path,
        asset_type="character",
        background="transparent background when possible",
        placeholder=placeholder,
    )


def generate_cover_image(prompt: str, output_path: str | Path, placeholder: bool = False) -> Path:
    """Generate one cover image as PNG without readable title text."""
    return _generate_image(
        prompt,
        output_path,
        asset_type="cover",
        background="clean full-page background with open space for title added later",
        placeholder=placeholder,
    )


def generate_coloring_page(prompt: str, output_path: str | Path, placeholder: bool = False) -> Path:
    """Generate one coloring page line-art PNG."""
    line_art_prompt = f"{prompt}. Black and white coloring page, thick outlines, no shading"
    return _generate_image(
        line_art_prompt,
        output_path,
        asset_type="coloring_page",
        background="clean white background",
        placeholder=placeholder,
    )


def generate_icon(prompt: str, output_path: str | Path, placeholder: bool = False) -> Path:
    """Generate one small icon-style PNG."""
    return _generate_image(
        prompt,
        output_path,
        asset_type="icon",
        background="transparent background when possible",
        placeholder=placeholder,
    )
