# Working on page-extract

## What this package is, and is not

It turns a web page into data and redraws the visuals worth keeping. It is not a
CMS, a publisher, a scraper framework or an LLM wrapper. Anything that knows
about *your* content model belongs in the project consuming this, not here.

The test: **would a second, unrelated project want this unchanged?** If the
answer needs a "well, if they also..." then it does not belong here.

## Rules

1. **No network in tests.** Every test builds its own fixture in-process. There
   is one HTTP module (`fetch.py`) and tests do not touch it.
2. **No colour literals in figure builders.** Take colours from
   `brand.color(name)`. A hard-coded hex is the one thing that stops another
   project adopting a builder.
3. **Never define a red/green pair as a semantic default.** In any domain with a
   direction, green and red mean up and down; using them for "option A vs B"
   tells the reader something untrue. Series colours are blue and slate.
4. **Every figure builder documents `WHEN_TO_PICK` and `SCHEMA`**, and
   `WHEN_TO_PICK` must name what to use *instead* when it does not fit. A test
   enforces both being non-empty; only you can enforce them being useful.
5. **Errors are typed.** Raise from `page_extract.errors` so a caller can catch
   one family. A bare `ValueError` out of a builder for bad params is fine;
   anything about fetching, extracting, rasterizing or branding is not.
6. **The CLI prints what it wrote.** Every verb ends by naming its output paths.
7. **Assume the machine is Windows.** Read and write files with an explicit
   `encoding="utf-8"` - a Windows default is cp1252 and will mangle or refuse
   real page text. Never assume a console can print what you extracted. Never
   assume an external program exists: probe for it, and when it is absent say
   what to install *on this platform*, and degrade rather than fail if the rest
   of the work is still usable. See [docs/windows.md](docs/windows.md).

## Adding a figure builder

See [docs/figures.md](docs/figures.md#adding-a-builder). Register it in
`figures/__init__.py` and add one entry to `CASES` in the test file; the
parametrized tests then cover it.

## Running the tests

```bash
python3 -m pytest tests/ -q
```

They are fast, hermetic and cover extraction, brand handling, SVG escaping and
wrapping, all builders, the format policy, chart recovery against a chart drawn
in the test, and image metrics.

## Releasing

Bump `version` in `pyproject.toml`, tag `v<version>`, push both. Consumers pin by
tag.
