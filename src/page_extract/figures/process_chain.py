"""Ordered steps, each flowing into the next."""
from __future__ import annotations

from .. import svgkit as K

W, H = 1200, 675

WHEN_TO_PICK = """
3-5 steps where the order is the point and each step is one short action. The
arrows are the content, which is why this is a drawing rather than a numbered
list. If a step needs more than a sentence, or the reader has to tick steps off,
use a live steps component instead.
"""

SCHEMA = {
    "title": "str, <=70 (optional)",
    "steps": "3-5 x {label <=26, note <=70 (optional)}",
    "caption": "str, <=110 (optional)",
}


def build(brand, p):
    steps = list(p["steps"])[:5]
    if len(steps) < 3:
        raise ValueError("process_chain needs at least 3 steps")

    out = []
    top = 40
    if p.get("title"):
        out.append(K.text(brand, 64, 78, p["title"], 36, "700", brand.color("ink")))
        top = 120

    pad, gap = 64, 34
    avail = W - pad * 2 - gap * (len(steps) - 1)
    card_w = avail / len(steps)
    # Height follows the content: badge, label, and the notes only if any step
    # has one. Fixing it instead left a third of the canvas empty.
    has_note = any(s.get("note") for s in steps)
    card_h = 250 if has_note else 172
    y = top + (H - top - 60 - card_h) / 2

    for i, step in enumerate(steps):
        x = pad + i * (card_w + gap)
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{card_w:.1f}" '
                   f'height="{card_h:.1f}" rx="16" fill="{brand.color("panel_a")}" '
                   f'stroke="{brand.color("line_a")}" stroke-width="2.5"/>')
        badge_cy = y + 48
        out.append(f'<circle cx="{x + card_w / 2:.1f}" cy="{badge_cy:.1f}" r="26" '
                   f'fill="{brand.color("ink")}"/>')
        out.append(K.text(brand, x + card_w / 2, badge_cy + 10, str(i + 1), 26, "700",
                          brand.color("accent"), "middle"))
        out.append(K.block(brand, x + card_w / 2, y + 122, step["label"], 24, 18,
                           brand.color("ink"), 28, "700"))
        if step.get("note"):
            out.append(K.block(brand, x + card_w / 2, y + 196, step["note"], 19, 24,
                               brand.color("ink_3"), 24))
        if i < len(steps) - 1:
            ax = x + card_w + 6
            ay = y + card_h / 2
            out.append(f'<path d="M{ax:.1f},{ay:.1f} L{ax + gap - 18:.1f},{ay:.1f}" '
                       f'stroke="{brand.color("accent")}" stroke-width="3" fill="none"/>')
            out.append(f'<polygon points="{ax + gap - 6:.1f},{ay:.1f} '
                       f'{ax + gap - 20:.1f},{ay - 8:.1f} {ax + gap - 20:.1f},{ay + 8:.1f}" '
                       f'fill="{brand.color("accent")}"/>')

    if p.get("caption"):
        out.append(K.text(brand, W / 2, H - 22, p["caption"], 20, "400",
                          brand.color("ink_3"), "middle"))
    return K.canvas(brand, W, H, "".join(out))
