# page-extract

Turn a web page into a folder you can build from: its substance as data, its
visuals measured and sorted, and the ones worth keeping **redrawn in your own
brand** instead of re-hosted.

```
out/
  harvest.json          every source, its headings, and the visual inventory
  contact-sheet.jpg     ALL images from ALL pages, on one labelled grid
  s1/extract.json       one page: prose blocks, tables as data, image records
  s2/extract.json
  assets/               the downloaded images, with pixel metrics attached
```

It does one job and has no opinion about what you do with the result. There is
no database, no CMS, no publishing step, no content model, and no LLM.

## Why it exists

Rebuilding a competitor's page by hand is slow, and handing the raw HTML to a
language model is expensive and mostly wasted — a 500 KB page is perhaps 4 KB of
substance. This package does every mechanical part deterministically so a model
only ever sees the small part that needs judgment:

- **Extraction** turns a page into ~4 KB of structured data.
- **One contact sheet** replaces "look at 14 images" with "look at 1".
- **Chart reading** recovers an OHLC series from a *screenshot* of a chart, by
  colour segmentation, so numbers are read off pixels rather than invented.
- **Figure builders** redraw a visual from parameters, in your palette, with
  your watermark — so nothing of the source's ships.

## Install

```bash
pip install git+https://github.com/miladsafaei-me/page-extract
page-extract doctor
```

If `page-extract` is not a recognised command, pip put it somewhere not on your
PATH — usual on Windows. Everything also works as:

```bash
python -m page_extract doctor
```

`doctor` reports what is present and what is not; `doctor --fix` pip-installs
whatever pip can supply, into the same environment.

### The one thing outside pip

Turning a drawn figure into a `.webp` needs an SVG rasterizer, and no rasterizer
ships a usable Windows wheel — every candidate ends up needing a cairo library.
So three backends are tried in order, and **you almost certainly already have
one**:

| Backend | Where it comes from |
|---|---|
| `rsvg-convert` | `dnf install librsvg2-tools` · `apt install librsvg2-bin` · `brew install librsvg` |
| `cairosvg` | `pip install "page-extract[cairo]"` — needs a cairo library, so Linux and macOS |
| **a headless browser** | Chrome, Edge, Chromium or Brave, already installed. **On Windows this is why nothing needs installing: Edge ships with it.** |

Installed somewhere unusual? `PAGE_EXTRACT_BROWSER=C:\path\to\msedge.exe`.

**Without any of them nothing is lost except the `.webp`** — the `.svg` is always
written, and it is the more useful artifact anyway if the page can embed SVG.

## Use

```bash
# Fetch pages, extract them, measure and sheet every image
page-extract harvest URL [URL ...] --out ./out

# Recover a candle series from a chart screenshot, and check it by eye
page-extract chart out/assets/s1-img11.bin \
    --bounds 6,34,800,392 --low 4005 --high 4130 \
    --preview out/chart-check.png

# Draw a figure in your brand and rasterize it
page-extract figure hub_spokes params.json --out out/fig-1 --logo mylogo.svg
page-extract figure hub_spokes params.json --out out/fig-1 --backend browser

# What builders exist, and when to pick each
page-extract builders

# Markup or picture? Ask about one shape, or print the rule
page-extract policy hub_spokes
page-extract policy
```

| Verb | What it does |
|---|---|
| `doctor` | Check the install, name what is missing; `--fix` installs it |
| `harvest` | N URLs → one workspace: extracts, downloads, measures, sheets |
| `chart` | Chart screenshot → OHLC series (+ a redraw to verify it by eye) |
| `figure` | Builder + params + brand → SVG and WebP |
| `builders` | List the builders with their "reach for this when" notes |
| `policy` | Should a given visual be live markup or a drawn picture? |

## Not every visual should become HTML

This is the decision the package is opinionated about, and `page-extract policy`
will argue it with you.

**Live markup** wins when the reader *does* something with the visual — sorts it,
hovers it, expands it — or when it must reflow onto a phone. Text stays
selectable, translatable, themeable and readable by search engines.

**A drawn picture** wins when the layout *is* the information. A hub with its
parts arranged around it says "these are equal and they belong to that". A 2x2
says "this case is high on one axis and low on the other". Stack either into
markup and the relationship is simply gone. Pictures also survive in RSS, in
email, and as an OG card, where markup does not.

When both would work, prefer markup.

## Brands

A brand is twelve lines of JSON, so adopting this package means writing a file
rather than forking the drawing code.

```json
{
  "name": "Acme",
  "logo": "assets/acme-logo.svg",
  "watermark_corner": "top-right",
  "palette": { "accent": "#41FFA0", "ink": "#0B1220" }
}
```

Every unspecified colour falls back to a neutral default, so a logo alone is
enough to start: `Brand.from_logo("acme.svg")` even reads the accent colour out
of the mark.

One palette choice is deliberate: **no red/green pair is defined as a semantic
colour.** In any domain with a direction — trading above all — green and red
mean up and down. Using them for "option A vs option B" tells the reader
something untrue, so the series colours are blue and slate instead.

## As a library

```python
from page_extract import Brand, extract_url, decide
from page_extract.figures import build
from page_extract.raster import svg_to_webp

doc = extract_url("https://example.com/article")
print(doc.word_count, doc.headings, len(doc.tables))

if decide("hub_spokes").format == "figure":
    svg = build("hub_spokes", Brand.from_logo("logo.svg"), {
        "hub": "Binary option",
        "spokes": [{"label": "Strike"}, {"label": "Direction"}, {"label": "Expiry"}],
    })
    open("fig.svg", "w").write(svg)
    svg_to_webp("fig.svg", "fig.webp", width=1200)
```

## Docs

- [`docs/usage.md`](docs/usage.md) — the full walkthrough, verb by verb
- [`docs/figures.md`](docs/figures.md) — every builder, its params, and how to add one
- [`docs/charts.md`](docs/charts.md) — how chart reading works and when it fails
- [`docs/windows.md`](docs/windows.md) — running on Windows: the two things that differ
- [`docs/llm-contract.md`](docs/llm-contract.md) — the seam: what to hand a model, and what never to

## Licence

MIT.
