# Usage

## The shape of a run

Everything happens inside one **workspace** directory. A workspace holds any
number of source pages, because the interesting jobs are rarely one-to-one:
two thin pages often deserve one article, one broad page can owe several, and
sometimes all you want is a single visual out of a page you will otherwise
ignore.

```bash
page-extract harvest \
    https://example.com/a \
    https://example.com/b \
    --out ./out
```

```
out/
  harvest.json        the manifest: every source, plus the visual inventory
  contact-sheet.jpg   every image from every source, labelled s1#3, s2#7, ...
  s1/extract.json     source 1 as data
  s2/extract.json
  assets/             s1-img03.bin, s1-img04.bin, ... with metrics in harvest.json
```

A failed source does not stop the run — it lands in `harvest.json` with its
error, and the rest continues.

## What `extract.json` holds

```jsonc
{
  "url": "...",
  "title": "...",
  "meta_description": "...",
  "word_count": 4549,
  "blocks": [                       // the article in reading order
    {"type": "h2", "text": "What are binary options?"},
    {"type": "p",  "text": "..."},
    {"type": "table_ref", "index": 0},
    {"type": "image_ref", "index": 3}
  ],
  "tables": [                       // tables as DATA, not markup
    {"header": ["Metric", "A", "B"],
     "rows": [["Cost", "10", "20"]],
     "shape": [1, 3],
     "numeric_columns": [1, 2],
     "comparison_like": true}
  ],
  "images": [
    {"index": 3, "src": "https://...", "alt": "...", "caption": "...",
     "width": 860, "height": 484, "kind": "infographic"}
  ],
  "stat_sentences": [               // prose that is really a table in hiding
    {"block": 12, "text": "Returns land between 70% and 85% ...",
     "hits": ["70%", "85%"]}
  ]
}
```

`stat_sentences` is worth a second look. A sentence carrying two or more numbers
is usually a visual the source never drew — those are the best candidates for a
figure of your own, because you are adding something rather than copying it.

## Image kinds

`kind` is guessed twice: first from the filename, alt text and declared size,
then refined against the pixels.

| kind | Means |
|---|---|
| `chrome` | Logo, icon, avatar, badge — never content. Not downloaded. |
| `chart` | A price or data chart. Try `page-extract chart` on it. |
| `infographic` | Flat art with text — the main thing worth redrawing. |
| `screenshot` | A capture of an interface. |
| `photo` | Even, low-contrast field — a photograph or a dark UI capture. |
| `banner` | Very wide; usually decoration. |
| `unknown` | Nothing decided it. Look at the sheet. |

The classification is cheap and fallible on purpose. Its job is to throw away
chrome before anything expensive looks at the rest; the contact sheet settles
what is left.

## The contact sheet

This is the point of the harvest step. Every kept image from every source is
composed into one labelled grid, four to a row:

```
s1#3   s1#4   s1#5   s1#6
s1#7   s1#8   s1#9   s1#10
s2#0   s2#1   s2#2   s2#3
```

Look at it once. Judging fourteen images individually costs roughly ten times as
much as judging one grid, whether the eyes are yours or a model's, and side by
side is genuinely easier to judge.

Write down, for each visual worth keeping, **what it does** — "hub with four
spokes", "7x3 comparison", "candlestick chart with an entry annotation". Not
which component or builder it will become: that decision belongs downstream,
and mixing the two is how a visual plan ends up copying the source's choices
instead of making its own.

## Reading a chart

```bash
page-extract chart out/assets/s1-img11.bin \
    --bounds 6,34,800,392 \
    --low 4005 --high 4130 \
    --preview out/chart-check.png
```

`--bounds x0,y0,x1,y1` crops to the plot area, excluding the toolbar, the axis
strip and any legend. Without it the reader usually still works, but coloured
chrome can survive as spurious bars.

`--low` / `--high` are the prices at the bottom and top of the axis, read off
the screenshot. Without them the series stays normalized 0-1, which is fine if
you only want the shape.

**Always pass `--preview` the first time.** It redraws the recovered series as
its own image; put it next to the screenshot and the two shapes either match or
they do not. That takes a second and is far more informative than reading JSON.

See [charts.md](charts.md) for how it works and when it fails.

## Drawing a figure

```bash
page-extract builders                       # what exists, and when to pick it
page-extract figure hub_spokes params.json --out out/fig-1 --logo logo.svg
```

Writes `out/fig-1.svg` and `out/fig-1.webp`. Pass `--brand brand.json` instead of
`--logo` once you have a brand file. See [figures.md](figures.md).

## Deciding the format

```bash
page-extract policy                         # the rule, in a paragraph
page-extract policy hub_spokes              # figure (hub_spokes): position is ...
page-extract policy table --rows 7          # component: its content is data ...
page-extract policy table --rows 3 --no-reflow
```

The verb answers from the shape of the job and always says why, so overriding it
is a decision rather than an accident.
