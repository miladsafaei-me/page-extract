# Figures

A figure is a drawing generated from parameters: no hand-written SVG, no copied
markup, and every one carries the brand's watermark.

```python
from page_extract import Brand
from page_extract.figures import build
from page_extract.raster import svg_to_webp

brand = Brand.from_logo("logo.svg")
open("fig.svg", "w").write(build("hub_spokes", brand, params))
svg_to_webp("fig.svg", "fig.webp", width=1200)
```

All builders draw at 1200x675 (16:9) on the brand's paper colour.

## The four builders

### `hub_spokes`

A central concept and 3-6 named parts that belong to it, where **no part comes
before another**. The single most common shape in stock infographics, and a real
drawing: the parts surround the centre because they are equal, and a bulleted
list quietly loses that.

```json
{
  "title": "What a binary option is made of",
  "hub": "Binary option",
  "hub_note": "one contract, four fixed parts",
  "spokes": [
    {"label": "Strike price", "note": "The reference the outcome is measured against"},
    {"label": "Direction",    "note": "Above or below, nothing in between"},
    {"label": "Expiry",       "note": "Sixty seconds or a full day"}
  ],
  "caption": "None of which you can change once the contract is open."
}
```

Reach for `process_chain` instead when the parts are ordered, or live markup
when each part needs a paragraph.

### `process_chain`

3-5 ordered steps, arrows between them. The arrows are the content.

```json
{
  "title": "How a binary option reaches its outcome",
  "steps": [
    {"label": "Pick the strike", "note": "Fixed when you open the contract"},
    {"label": "Pick the expiry", "note": "The contract has no life beyond it"},
    {"label": "Settle, once",    "note": "Payout credited, or the stake is gone"}
  ],
  "caption": "Four decisions, then nothing you can do."
}
```

Card height follows whether any step has a `note`, so a bare chain does not
leave a third of the canvas empty.

### `quadrant`

Exactly four cases produced by crossing two conditions. Position **is** the
meaning — which half of each axis a case sits in.

```json
{
  "title": "Which contract suits which edge",
  "x_axis": {"label": "How long you hold", "low": "Minutes", "high": "Weeks"},
  "y_axis": {"label": "Do you manage it?", "low": "Set and forget", "high": "Actively"},
  "cells": [
    {"at": "bl", "label": "Binary option", "note": "Direction in a fixed window", "tone": "good"},
    {"at": "tr", "label": "Traditional options", "note": "Spreads and rolls", "tone": "good"},
    {"at": "tl", "label": "Day-traded options", "note": "Gamma risk dominates", "tone": "warn"},
    {"at": "br", "label": "Long-dated binary", "note": "Rarely worth it", "tone": "bad"}
  ]
}
```

`at` is `tl` / `tr` / `bl` / `br`. `tone` is `good` / `bad` / `warn` / `neutral`.

### `contrast_table`

Two subjects compared row by row on 2-4 axes — what most "A or B" infographics
collapse to once their decoration is stripped.

```json
{
  "title": "One name, two different contracts",
  "subtitle": "What actually changes between them",
  "left_title": "Binary option",  "left_note": "one decision, one settlement",
  "right_title": "Traditional option", "right_note": "a position you keep managing",
  "rows": [
    {"label": "Payout", "left": "Fixed before you enter", "right": "Moves with price and time"},
    {"label": "Exit control", "left": "None — it settles at expiry", "right": "Sell or hedge any time"}
  ]
}
```

More than four rows, or numbers a reader will want to scan on a phone? Use a
live comparison table instead.

## Adding a builder

A builder is one module in `page_extract/figures/` exposing three names:

```python
"""One line on what this draws."""
from .. import svgkit as K

W, H = 1200, 675

WHEN_TO_PICK = """
When to reach for this, and — just as important — which builder or which live
component to use instead when it does not fit.
"""

SCHEMA = {"title": "str, <=70", "items": "3-6 x {label <=26}"}


def build(brand, p):
    out = [K.text(brand, 64, 78, p["title"], 40, "700", brand.color("ink"))]
    ...
    return K.canvas(brand, W, H, "".join(out))
```

Then register it in `figures/__init__.py`. `K.canvas` paints the paper and adds
the watermark, so a builder never handles either.

Three rules the existing builders follow:

1. **Take colours from `brand.color(name)`**, never a literal. A hard-coded hex
   is the one thing that stops a second project from adopting the builder.
2. **Use `K.block` for any text that might wrap.** It centres a wrapped
   paragraph on a point, which is what nearly every cell needs.
3. **Say what you will not do.** `WHEN_TO_PICK` earns its place by naming the
   cases that belong somewhere else; without that, every builder looks equally
   plausible and the choice becomes arbitrary.

## Testing a builder

`tests/test_page_extract.py` parametrizes over every registered builder and
checks that it produces well-formed XML and documents itself. Adding a builder
plus one entry in that test's `CASES` dict is the whole obligation.
