"""SVG to PNG and WebP, without a browser.

Prefers `rsvg-convert` (fast, faithful, one package on every Linux), falls back
to `cairosvg` if it is installed. A headless browser would render more exotic
SVG, but figures drawn by this package deliberately stay inside the subset both
of these handle, so the output does not depend on having Chromium around.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .errors import RasterError


def available() -> str | None:
    if shutil.which("rsvg-convert"):
        return "rsvg-convert"
    try:
        import cairosvg  # noqa: F401
        return "cairosvg"
    except ImportError:
        return None


def svg_to_png(svg_path, png_path, width=None) -> Path:
    svg_path, png_path = Path(svg_path), Path(png_path)
    tool = available()
    if tool == "rsvg-convert":
        cmd = ["rsvg-convert", str(svg_path), "-o", str(png_path)]
        if width:
            cmd[2:2] = ["-w", str(width)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RasterError(f"rsvg-convert failed: {proc.stderr.strip()}")
    elif tool == "cairosvg":
        import cairosvg
        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path),
                         output_width=width)
    else:
        raise RasterError(
            "no SVG rasterizer found. Install rsvg-convert "
            "(dnf install librsvg2-tools / apt install librsvg2-bin) "
            "or `pip install page-extract[cairo]`.")
    return png_path


def svg_to_webp(svg_path, webp_path, width=None, quality=88, keep_png=False):
    """Render an SVG straight to WebP, the format a figure ships in."""
    from PIL import Image
    svg_path, webp_path = Path(svg_path), Path(webp_path)
    png_path = webp_path.with_suffix(".png")
    svg_to_png(svg_path, png_path, width)
    im = Image.open(png_path).convert("RGB")
    im.save(webp_path, "WEBP", quality=quality, method=6)
    if not keep_png:
        png_path.unlink(missing_ok=True)
    return webp_path, im.size
