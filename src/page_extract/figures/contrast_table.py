"""Two subjects set against each other on a handful of named axes."""
from __future__ import annotations

from .. import svgkit as K

W, H = 1200, 675

WHEN_TO_PICK = """
Two named things compared row by row on 2-4 axes. This is what most source
"A or B" infographics collapse to once their decoration is stripped. Use a live
comparison table instead when there are more than four rows, or when the cells
carry numbers a reader will want to sort or scan on a phone.
"""

SCHEMA = {
    "title": "str, <=70", "subtitle": "str, <=110 (optional)",
    "left_title": "str, <=28", "left_note": "str, <=40 (optional)",
    "right_title": "str, <=28", "right_note": "str, <=40 (optional)",
    "rows": "2-4 x {label <=18, left <=60, right <=60}",
}


def build(brand, p):
    rows = list(p["rows"])[:4]
    out = [K.text(brand, 64, 78, p["title"], 40, "700", brand.color("ink"))]
    if p.get("subtitle"):
        out.append(K.text(brand, 64, 116, p["subtitle"], 23, "400", brand.color("ink_3")))

    head_y, head_h = 150, 74
    left_x, right_x, col_w = 372, 786, 386
    for x, title, note, fill, stroke in (
        (left_x, p["left_title"], p.get("left_note"), "panel_a", "line_a"),
        (right_x, p["right_title"], p.get("right_note"), "panel_b", "line_b"),
    ):
        out.append(f'<rect x="{x}" y="{head_y}" width="{col_w}" height="{head_h}" '
                   f'rx="14" fill="{brand.color(fill)}" stroke="{brand.color(stroke)}" '
                   f'stroke-width="2"/>')
        out.append(K.text(brand, x + col_w / 2, head_y + 36, title, 27, "700",
                          brand.color("ink"), "middle"))
        if note:
            out.append(K.text(brand, x + col_w / 2, head_y + 60, note, 19, "400",
                              brand.color("ink_3"), "middle"))

    top, bottom, gap = 252, H - 40, 18
    row_h = (bottom - top - gap * (len(rows) - 1)) / len(rows)
    for i, row in enumerate(rows):
        y = top + i * (row_h + gap)
        out.append(f'<rect x="64" y="{y:.1f}" width="292" height="{row_h:.1f}" '
                   f'rx="14" fill="{brand.color("ink")}"/>')
        out.append(K.text(brand, 84, y + row_h / 2 + 10, row["label"], 26, "700",
                          brand.color("accent")))
        for x, txt, fill, stroke in ((left_x, row["left"], "panel_a", "line_a"),
                                     (right_x, row["right"], "panel_b", "line_b")):
            out.append(f'<rect x="{x}" y="{y:.1f}" width="{col_w}" height="{row_h:.1f}" '
                       f'rx="14" fill="{brand.color(fill)}" fill-opacity="0.5" '
                       f'stroke="{brand.color(stroke)}" stroke-width="2"/>')
            out.append(K.block(brand, x + col_w / 2, y + row_h / 2, txt, 23, 26))
    return K.canvas(brand, W, H, "".join(out))
