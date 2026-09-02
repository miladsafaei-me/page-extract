"""SVG primitives the figure builders share, all brand-aware.

Nothing here draws a whole figure. It exists so a builder is a layout decision
and nothing else — text placement, wrapping and the watermark are solved once.
"""
from __future__ import annotations

import re
from pathlib import Path

from .brand import Brand

_ESCAPES = ((("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"), ('"', "&quot;")))


def esc(s: str) -> str:
    out = str(s)
    for a, b in _ESCAPES:
        out = out.replace(a, b)
    return out


def text(brand: Brand, x, y, s, size=24, weight="400", fill=None, anchor="start"):
    fill = fill or brand.color("ink_2")
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{esc(brand.font)}" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}">{esc(s)}</text>')


def wrap(s: str, width: int) -> list[str]:
    """Greedy wrap by character count. Deliberately crude: figures use short
    strings, and a real text-measurement pass would need a font engine."""
    words, lines, cur = str(s).split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if len(trial) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def block(brand: Brand, cx, cy, s, size=23, width=26, fill=None, line_h=30, weight="400"):
    """Wrapped text centred on a point — the shape most figure cells need."""
    lines = wrap(s, width)
    top = cy - (len(lines) - 1) * line_h / 2 + size * 0.36
    return "".join(text(brand, cx, top + i * line_h, ln, size, weight, fill, "middle")
                   for i, ln in enumerate(lines))


def _logo_group(brand: Brand, x, y, scale, opacity=0.9):
    raw = Path(brand.logo).read_text(encoding="utf-8", errors="replace")
    fill = re.search(r"fill:\s*(#[0-9a-fA-F]{3,8})", raw)
    color = fill.group(1) if fill else brand.color("accent")
    body = re.sub(r"<\?xml.*?\?>", "", raw, flags=re.S)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r"<defs>.*?</defs>", "", body, flags=re.S)
    inner = re.search(r"<svg[^>]*>(.*)</svg>", body, re.S)
    inner = inner.group(1) if inner else body
    inner = re.sub(r'class="[^"]*"', f'fill="{color}"', inner)
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({scale:.5f})" '
            f'opacity="{opacity}">{inner}</g>')


def watermark(brand: Brand, canvas_w, canvas_h, pad=26, opacity=0.85) -> str:
    """The destination's mark, on a plate so it stays legible on any background.

    Placed in the corner source sites usually stamp, so a redrawn visual carries
    *your* mark exactly where a reader already looks for one. A brand with no
    logo, or `watermark_corner: "none"`, renders nothing — the figure is still
    yours, it just does not say so.
    """
    if brand.logo is None or brand.watermark_corner == "none":
        return ""
    w = brand.watermark_width
    h = w / brand.logo_aspect
    plate_w, plate_h = w + 28, h + 20
    right, bottom = canvas_w - plate_w - pad, canvas_h - plate_h - pad
    x, y = {
        "top-right": (right, pad), "top-left": (pad, pad),
        "bottom-right": (right, bottom), "bottom-left": (pad, bottom),
    }[brand.watermark_corner]
    # The logo's own viewBox width, derived from the aspect the brand declares.
    native_w = brand.logo_aspect * 146.63
    scale = w / native_w
    return (f'<g class="pgx-watermark">'
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{plate_w:.1f}" '
            f'height="{plate_h:.1f}" rx="10" fill="{brand.color("ink")}" opacity="0.92"/>'
            + _logo_group(brand, x + 14, y + 10, scale, opacity) + "</g>")


def canvas(brand: Brand, width, height, body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}">'
            f'<rect width="{width}" height="{height}" fill="{brand.color("paper")}"/>'
            f"{body}{watermark(brand, width, height)}</svg>")
