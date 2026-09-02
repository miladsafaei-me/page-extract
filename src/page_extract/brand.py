"""Who the output belongs to.

Every drawn figure carries a brand: its palette, its type, and its watermark.
That is the whole reason this package can redraw someone else's visual instead
of re-hosting it — the result is *yours*, and it says so in the corner.

A brand is a small JSON file, so a second project adopts this package by
writing twelve lines rather than by forking the drawing code:

    {
      "name": "Example",
      "logo": "assets/logo.svg",
      "watermark_corner": "top-right",
      "palette": {"ink": "#0B1220", "accent": "#41FFA0", ...}
    }
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .errors import BrandError

#: A neutral palette that reads correctly on white without belonging to anyone.
#: Note what is absent: no red/green pair is defined as a *semantic* colour here.
#: In trading, finance and anything with a direction, green and red mean up and
#: down; using them for "option A vs option B" tells the reader something untrue.
#: Series colours are deliberately blue and slate instead.
DEFAULT_PALETTE = {
    "paper": "#FFFFFF",
    "ink": "#0B1220",
    "ink_2": "#334155",
    "ink_3": "#64748B",
    "accent": "#2563EB",
    "panel_a": "#F1F5F9",
    "panel_b": "#EEF2FF",
    "line_a": "#94A3B8",
    "line_b": "#6366F1",
    "good": "#15803D",
    "bad": "#B91C1C",
    "warn": "#B45309",
}

DEFAULT_FONT = "Liberation Sans, Arial, Helvetica, sans-serif"
CORNERS = ("top-right", "top-left", "bottom-right", "bottom-left", "none")


@dataclass
class Brand:
    """Everything a figure needs to look like it came from one place."""

    name: str = "page-extract"
    logo: Path | None = None
    logo_aspect: float = 423.93 / 146.63          # width / height of the mark
    watermark_corner: str = "top-right"
    watermark_width: int = 132
    font: str = DEFAULT_FONT
    palette: dict = field(default_factory=lambda: dict(DEFAULT_PALETTE))

    def __post_init__(self):
        if self.watermark_corner not in CORNERS:
            raise BrandError(
                f"watermark_corner must be one of {CORNERS}, got {self.watermark_corner!r}")
        merged = dict(DEFAULT_PALETTE)
        merged.update(self.palette or {})
        self.palette = merged
        if self.logo is not None:
            self.logo = Path(self.logo)
            if not self.logo.exists():
                raise BrandError(f"brand logo not found: {self.logo}")

    def color(self, key: str) -> str:
        try:
            return self.palette[key]
        except KeyError:
            raise BrandError(f"palette has no colour {key!r}; "
                             f"known: {sorted(self.palette)}") from None

    @classmethod
    def load(cls, path) -> "Brand":
        """Read a brand JSON file. Relative asset paths resolve next to it."""
        path = Path(path)
        if not path.exists():
            raise BrandError(f"no brand file at {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise BrandError(f"{path} is not valid JSON: {exc}") from None
        logo = data.get("logo")
        if logo:
            logo = (path.parent / logo).resolve()
        return cls(
            name=data.get("name", "page-extract"),
            logo=logo,
            logo_aspect=float(data.get("logo_aspect", cls.logo_aspect)),
            watermark_corner=data.get("watermark_corner", "top-right"),
            watermark_width=int(data.get("watermark_width", 132)),
            font=data.get("font", DEFAULT_FONT),
            palette=data.get("palette") or {},
        )

    @classmethod
    def from_logo(cls, logo_path, name=None, **kw) -> "Brand":
        """The shortcut: a mark and the defaults. Picks the accent colour out of
        the SVG's own fill, so a logo alone already produces coherent figures."""
        logo_path = Path(logo_path)
        if not logo_path.exists():
            raise BrandError(f"no logo at {logo_path}")
        palette = dict(kw.pop("palette", {}) or {})
        found = re.search(r"fill:\s*(#[0-9a-fA-F]{3,8})", logo_path.read_text(
            encoding="utf-8", errors="replace"))
        if found and "accent" not in palette:
            palette["accent"] = found.group(1)
        return cls(name=name or logo_path.stem, logo=logo_path, palette=palette, **kw)
