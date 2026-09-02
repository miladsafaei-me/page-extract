"""Read an OHLC series back out of a picture of a candlestick chart.

A screenshot of a chart is data that has been flattened into pixels. Colour
segmentation gets it back: bullish and bearish candles are the only strongly
green and strongly red things in the frame, each candle is a contiguous vertical
run, and the widest columns of that run are its body while the thin centre line
is its wick.

The result is normalized 0-1 on the price axis, because the pixels cannot know
what the axis said. `rescale` maps it onto real numbers once a caller supplies
the range. No model is involved, so reading a chart costs nothing.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


def _bull(r, g, b):
    return g > 80 and g - r > 25 and g - b > 20


def _bear(r, g, b):
    return r > 80 and r - g > 32 and r - b > 25


def _column_run(px, x, y0, y1):
    """Longest contiguous coloured run in one column: (top, bottom, bull, bear).

    Contiguity is what keeps legend swatches, toolbar icons and axis ticks out:
    they are coloured, but they are not part of the candle's vertical run.
    """
    best = start = None
    bull = bear = 0
    for y in range(y0, y1 + 1):
        r, g, b = px[x, y][:3]
        hb, hr = _bull(r, g, b), _bear(r, g, b)
        if hb or hr:
            if start is None:
                start, bull, bear = y, 0, 0
            bull += hb
            bear += hr
        elif start is not None:
            cand = (start, y - 1, bull, bear)
            if best is None or cand[1] - cand[0] > best[1] - best[0]:
                best = cand
            start = None
    if start is not None:
        cand = (start, y1, bull, bear)
        if best is None or cand[1] - cand[0] > best[1] - best[0]:
            best = cand
    return best


def scan(im, bounds=None, min_run=2):
    w, h = im.size
    x0, y0, x1, y1 = bounds or (0, 0, w - 1, h - 1)
    px = im.load()
    cols = []
    for x in range(max(0, x0), min(w - 1, x1) + 1):
        run = _column_run(px, x, max(0, y0), min(h - 1, y1))
        if run and run[1] - run[0] >= min_run:
            cols.append((x, *run))
    return cols


def group(cols, gap=1, outlier_factor=3.0):
    """Merge adjacent columns into candles.

    Two corrections make this work on real screenshots. Dark themes draw candles
    edge to edge, so a merged run far wider than the modal candle is split back
    into equal-pitch parts. And any candle towering over its neighbours by more
    than `outlier_factor` is chrome that survived the crop, not a bar.
    """
    groups, cur = [], []
    for col in cols:
        if not cur or col[0] - cur[-1][0] <= gap + 1:
            cur.append(col)
        else:
            groups.append(cur)
            cur = [col]
    if cur:
        groups.append(cur)

    widths = sorted(len(g) for g in groups if len(g) >= 2)
    pitch = widths[len(widths) // 4] if widths else 0
    if pitch >= 2:
        split = []
        for g in groups:
            k = round(len(g) / pitch)
            if k >= 2 and len(g) >= 2 * pitch:
                size = len(g) / k
                for i in range(k):
                    part = g[int(i * size):int((i + 1) * size)]
                    if len(part) >= 2:
                        split.append(part)
            else:
                split.append(g)
        groups = split

    out = []
    for g in groups:
        if len(g) < 2:
            continue
        top, bottom = min(c[1] for c in g), max(c[2] for c in g)
        heights = sorted(c[2] - c[1] for c in g)
        median_h = heights[len(heights) // 2]
        body = [c for c in g if (c[2] - c[1]) <= median_h * 1.6] or g
        out.append({"x": g[0][0], "cols": len(g), "high_px": top, "low_px": bottom,
                    "body_top_px": min(c[1] for c in body),
                    "body_bottom_px": max(c[2] for c in body),
                    "bullish": sum(c[3] for c in g) >= sum(c[4] for c in g)})

    if len(out) >= 6:
        spans = sorted(c["low_px"] - c["high_px"] for c in out)
        med = spans[len(spans) // 2] or 1
        ws = sorted(c["cols"] for c in out)
        wmed = ws[len(ws) // 2] or 1
        out = [c for c in out
               if (c["low_px"] - c["high_px"]) <= med * outlier_factor
               and c["cols"] <= wmed * 2.5]
    return out


def to_ohlc(candles) -> list[dict]:
    if not candles:
        return []
    lo = min(c["high_px"] for c in candles)
    hi = max(c["low_px"] for c in candles)
    span = max(1, hi - lo)

    def n(v):                       # pixel Y grows downward; price does not
        return round(1 - (v - lo) / span, 5)

    series = []
    for c in candles:
        h, low = n(c["high_px"]), n(c["low_px"])
        bt, bb = n(c["body_top_px"]), n(c["body_bottom_px"])
        o, cl = (bb, bt) if c["bullish"] else (bt, bb)
        series.append({"o": o, "h": max(h, low), "l": min(h, low), "c": cl})
    return series


def read(path, bounds=None) -> list[dict]:
    """The whole job: an image path in, a normalized OHLC series out."""
    return to_ohlc(group(scan(Image.open(path).convert("RGB"), bounds)))


def rescale(series, low: float, high: float, decimals: int = 2) -> list[dict]:
    """Map a normalized series onto the price range the chart's axis showed."""
    span = high - low
    return [{k: round(low + s[k] * span, decimals) for k in ("o", "h", "l", "c")}
            for s in series]


def preview(series, out_path, width=860, height=410, up="#3bb273", down="#df2c53"):
    """Draw the recovered series so the extraction can be judged by looking.

    Pair it with the source screenshot: if the two shapes match, the numbers are
    right, and no amount of staring at JSON would have told you that faster.
    """
    from PIL import ImageDraw
    im = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(im)
    if not series:
        return im
    pad = 14
    step = (width - 2 * pad) / len(series)
    body = max(2, int(step * 0.62))
    for i, s in enumerate(series):
        cx = pad + step * (i + 0.5)

        def y(v):
            return pad + (1 - v) * (height - 2 * pad)

        color = up if s["c"] >= s["o"] else down
        d.line([(cx, y(s["h"])), (cx, y(s["l"]))], fill=color, width=max(1, body // 6))
        top, bot = y(max(s["o"], s["c"])), y(min(s["o"], s["c"]))
        d.rectangle([cx - body / 2, top, cx + body / 2, max(bot, top + 1)], fill=color)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, quality=90)
    return im


def save(series, path) -> Path:
    path = Path(path)
    path.write_text(json.dumps(series), encoding="utf-8")
    return path
