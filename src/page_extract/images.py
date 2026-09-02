"""Download a page's images, measure them, and lay the whole set on one sheet.

The sheet is the point. Deciding what a page's visuals *are* is the one job here
that needs eyes — human or model — and eyes are the expensive part. Composing
every image into a single labelled grid turns "look at fourteen pictures" into
"look at one", which is roughly an order of magnitude cheaper and, in practice,
easier to judge because everything is side by side.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .fetch import download

CELL_W, LABEL_H, COLS = 470, 26, 4


def metrics(path) -> dict:
    """Cheap pixel statistics that separate a diagram from a photo or a chart.

    - `flat_share`   how much of the image is one single colour. Flat art is
                     high; a photograph or a screenshot is low.
    - `edge_density` proportion of strong edges. Text and line art are high.
    - `row_banding`  vertical variation in row brightness. Banded layouts
                     (tables, stacked cards) score high; even fields score low.
    """
    im = Image.open(path).convert("RGB")
    w, h = im.size
    small = im.resize((160, max(1, int(160 * h / w))))
    colors = small.getcolors(maxcolors=160 * 160) or []
    total = sum(c for c, _ in colors)
    gray = small.convert("L")
    hist = gray.filter(ImageFilter.FIND_EDGES).histogram()
    px = list(gray.tobytes())
    rows = [sum(px[y * gray.width:(y + 1) * gray.width]) / gray.width
            for y in range(gray.height)]
    mean = sum(rows) / len(rows)
    return {
        "size": [w, h],
        "aspect": round(w / h, 2),
        "distinct_colors": len(colors),
        "flat_share": round(max((c for c, _ in colors), default=0) / total, 3) if total else 0,
        "edge_density": round(sum(hist[60:]) / max(1, sum(hist)), 4),
        "row_banding": round(math.sqrt(sum((r - mean) ** 2 for r in rows) / len(rows)), 1),
    }


def refine_kind(kind: str, m: dict) -> str:
    """Upgrade the filename guess using the pixels, where they clearly disagree."""
    if kind == "chrome":
        return kind
    flat, edges, colors = m["flat_share"], m["edge_density"], m["distinct_colors"]
    if flat < 0.12 and edges < 0.10:
        return "photo"                       # even, low-contrast field
    if flat > 0.25 and edges > 0.10:
        return "infographic" if kind in ("unknown", "banner") else kind
    return kind


def collect(doc, out_dir, skip=("chrome",), label_prefix="") -> list[dict]:
    """Download every image worth keeping and attach its metrics in place."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    kept = []
    for img in doc.images:
        if img["kind"] in skip:
            continue
        dest = out_dir / f"{label_prefix}img{img['index']:02d}.bin"
        try:
            download(img["src"], dest)
            img["metrics"] = metrics(dest)
        except Exception as exc:                     # unreachable, truncated, odd format
            img["error"] = str(exc)
            dest.unlink(missing_ok=True)
            continue
        img["kind"] = refine_kind(img["kind"], img["metrics"])
        img["local"] = str(dest)
        img["label"] = f"{label_prefix}#{img['index']}" if label_prefix else f"#{img['index']}"
        kept.append(img)
    return kept


def contact_sheet(records, out_path, cols=COLS, cell_w=CELL_W) -> tuple[int, int]:
    """One labelled grid of every image, so classifying a set costs one look."""
    out_path = Path(out_path)
    thumbs = []
    for rec in records:
        im = Image.open(rec["local"]).convert("RGB")
        im = im.resize((cell_w, max(1, int(im.height * cell_w / im.width))))
        thumbs.append((rec, im))
    if not thumbs:
        raise ValueError("no images to lay out")
    cell_h = max(t.height for _, t in thumbs) + LABEL_H
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cell_w * cols, cell_h * rows), "white")
    draw = ImageDraw.Draw(sheet)
    for n, (rec, im) in enumerate(thumbs):
        x, y = (n % cols) * cell_w, (n // cols) * cell_h
        draw.rectangle([x, y, x + cell_w - 2, y + LABEL_H], fill="#111827")
        draw.text((x + 8, y + 7), rec.get("label") or Path(rec["local"]).name, fill="white")
        sheet.paste(im, (x, y + LABEL_H))
        draw.rectangle([x, y, x + cell_w - 2, y + cell_h - 2], outline="#9ca3af")
    sheet.save(out_path, quality=88)
    return sheet.size
