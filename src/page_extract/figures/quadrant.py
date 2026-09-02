"""Four cases, placed by two axes."""
from __future__ import annotations

from .. import svgkit as K

W, H = 1200, 675

WHEN_TO_PICK = """
Exactly four outcomes that are produced by crossing two conditions. Position IS
the meaning here — which half of each axis a case sits in — so flattening it to
four list items destroys the point. Use a live table when the two axes are not
really axes, only column headings.
"""

SCHEMA = {
    "title": "str, <=70 (optional)",
    "x_axis": "{label <=30, low <=22, high <=22}",
    "y_axis": "{label <=30, low <=22, high <=22}",
    "cells": "4 x {label <=30, note <=60 (optional), "
             "tone: good|bad|warn|neutral, at: tl|tr|bl|br}",
}

_TONE = {"good": ("good", "#F0FDF4"), "bad": ("bad", "#FEF2F2"),
         "warn": ("warn", "#FFFBEB"), "neutral": ("line_a", "#F8FAFC")}


def build(brand, p):
    out = []
    top = 40
    if p.get("title"):
        out.append(K.text(brand, 64, 74, p["title"], 34, "700", brand.color("ink")))
        top = 108

    left, right = 150, W - 60
    bottom = H - 96
    mid_x, mid_y = (left + right) / 2, (top + bottom) / 2
    cell_w, cell_h = (right - left) / 2, (bottom - top) / 2
    at_xy = {"tl": (left, top), "tr": (mid_x, top),
             "bl": (left, mid_y), "br": (mid_x, mid_y)}

    for cell in list(p["cells"])[:4]:
        x, y = at_xy[cell["at"]]
        stroke_key, fill = _TONE.get(cell.get("tone", "neutral"), _TONE["neutral"])
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_w:.1f}" '
                   f'height="{cell_h:.1f}" rx="14" fill="{fill}" '
                   f'stroke="{brand.color(stroke_key)}" stroke-width="2.5"/>')
        cy = y + cell_h / 2 - (16 if cell.get("note") else 0)
        out.append(K.block(brand, x + cell_w / 2, cy, cell["label"], 25, 20,
                           brand.color("ink"), 29, "700"))
        if cell.get("note"):
            out.append(K.block(brand, x + cell_w / 2, y + cell_h / 2 + 34,
                               cell["note"], 19, 30, brand.color("ink_3"), 23))

    # Axes drawn last, over the cells, so the cross reads as one shape.
    out.append(f'<line x1="{left}" y1="{mid_y:.1f}" x2="{right}" y2="{mid_y:.1f}" '
               f'stroke="{brand.color("ink")}" stroke-width="3"/>')
    out.append(f'<line x1="{mid_x:.1f}" y1="{top}" x2="{mid_x:.1f}" y2="{bottom}" '
               f'stroke="{brand.color("ink")}" stroke-width="3"/>')

    xa, ya = p["x_axis"], p["y_axis"]
    out.append(K.text(brand, left, bottom + 34, xa["low"], 19, "400", brand.color("ink_3")))
    out.append(K.text(brand, right, bottom + 34, xa["high"], 19, "400",
                      brand.color("ink_3"), "end"))
    out.append(K.text(brand, mid_x, bottom + 62, xa["label"], 22, "700",
                      brand.color("ink"), "middle"))
    out.append(f'<g transform="translate(96,{mid_y:.1f}) rotate(-90)">'
               + K.text(brand, 0, 0, ya["label"], 22, "700", brand.color("ink"), "middle")
               + "</g>")
    out.append(f'<g transform="translate(126,{top + 4:.1f}) rotate(-90)">'
               + K.text(brand, 0, 0, ya["high"], 19, "400", brand.color("ink_3"), "end")
               + "</g>")
    out.append(f'<g transform="translate(126,{bottom - 4:.1f}) rotate(-90)">'
               + K.text(brand, 0, 0, ya["low"], 19, "400", brand.color("ink_3"))
               + "</g>")
    return K.canvas(brand, W, H, "".join(out))
