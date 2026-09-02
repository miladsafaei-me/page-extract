"""One idea in the middle, its parts arranged around it."""
from __future__ import annotations

import math

from .. import svgkit as K

W, H = 1200, 675

WHEN_TO_PICK = """
A central concept and 3-6 named parts that belong to it, where no part comes
before another. This is the single most common shape in stock infographics, and
it is genuinely a drawing: the parts surround the centre because they are equal,
and a bulleted list quietly loses that. Reach for a process figure instead when
the parts are ordered, or a live list when each part needs a paragraph.
"""

SCHEMA = {
    "title": "str, <=70 (optional)",
    "hub": "str, <=34",
    "hub_note": "str, <=30 (optional)",
    "spokes": "3-6 x {label <=26, note <=44 (optional)}",
    "caption": "str, <=110 (optional)",
}

TONE_KEYS = ("accent", "line_b", "good", "warn", "bad", "ink_3")


def build(brand, p):
    spokes = list(p["spokes"])[:6]
    if len(spokes) < 3:
        raise ValueError("hub_spokes needs at least 3 spokes")

    out = []
    top = 30
    if p.get("title"):
        out.append(K.text(brand, W / 2, 66, p["title"], 36, "700",
                          brand.color("ink"), "middle"))
        top = 96

    cx, cy = W / 2, top + (H - top - 60) / 2
    hub_r = 104
    # Radii chosen so the widest node still clears the canvas edge with a margin.
    rx, ry = 430, (H - top - 90) / 2 - 8
    node_w, node_h = 250, 92

    for i, spoke in enumerate(spokes):
        angle = -math.pi / 2 + (2 * math.pi * i / len(spokes))
        nx, ny = cx + rx * math.cos(angle), cy + ry * math.sin(angle)
        tone = brand.color(TONE_KEYS[i % len(TONE_KEYS)])
        # Line stops at the hub edge so it never draws over the hub's own label.
        sx, sy = cx + hub_r * math.cos(angle), cy + hub_r * math.sin(angle)
        out.append(f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" '
                   f'stroke="{tone}" stroke-width="2.5" opacity="0.55"/>')
        out.append(f'<rect x="{nx - node_w / 2:.1f}" y="{ny - node_h / 2:.1f}" '
                   f'width="{node_w}" height="{node_h}" rx="14" '
                   f'fill="{brand.color("paper")}" stroke="{tone}" stroke-width="2.5"/>')
        label_y = ny - (10 if spoke.get("note") else 0)
        out.append(K.block(brand, nx, label_y, spoke["label"], 23, 22,
                           brand.color("ink"), 26, "700"))
        if spoke.get("note"):
            out.append(K.block(brand, nx, ny + 22, spoke["note"], 18, 30,
                               brand.color("ink_3"), 21))

    out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{hub_r}" '
               f'fill="{brand.color("ink")}"/>')
    hub_y = cy - (11 if p.get("hub_note") else 0)
    out.append(K.block(brand, cx, hub_y, p["hub"], 25, 16,
                       brand.color("accent"), 28, "700"))
    if p.get("hub_note"):
        out.append(K.block(brand, cx, cy + 34, p["hub_note"], 17, 20,
                           brand.color("panel_a"), 20))

    if p.get("caption"):
        out.append(K.text(brand, W / 2, H - 22, p["caption"], 20, "400",
                          brand.color("ink_3"), "middle"))
    return K.canvas(brand, W, H, "".join(out))
