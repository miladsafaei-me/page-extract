# Running on Windows

Everything works, and in the normal case nothing needs installing beyond the
package itself. This page exists because the two things that *do* differ on
Windows are both silent until they bite.

## 1. `page-extract` is not a recognised command

pip installs console scripts into a `Scripts\` directory that is very often not
on PATH. Nothing is broken; use the module entry point instead:

```
python -m page_extract doctor
python -m page_extract harvest https://example.com/a --out .\out
```

Every verb works identically that way. If `python` itself is not recognised,
try `py -m page_extract ...`.

## 2. Rasterizing SVG

Writing a figure's `.webp` needs an SVG rasterizer, and this is the one place
Windows genuinely differs: **no SVG rasterizer ships a usable Windows wheel.**
`cairosvg`, `svglib`+`reportlab` and `pycairo` all end up needing a cairo
library, which Windows does not have and pip cannot supply.

So the package tries a **headless browser** as well — and Windows always has
one, because Edge ships with the operating system. `page-extract doctor` will
normally say:

```
SVG rasterizer  (needed only to write .webp; the .svg is always written)
  [--  ] rsvg-convert  not installed — ...
  [--  ] cairosvg      not usable (ImportError) — ...
  [ok  ] browser       C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe

  will use: browser
```

If it does not find one, point at it directly:

```
set PAGE_EXTRACT_BROWSER=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
python -m page_extract doctor
```

Force it for one run with `--backend browser`.

### If there is no rasterizer at all

Nothing is lost but the `.webp`. The `.svg` is always written, `page-extract
figure` says so and exits with code **3** rather than dying, and an SVG is the
better artifact anyway wherever the page can embed one.

## 3. Non-English text in the console

A Windows console is cp1252 by default, so a Persian, Turkish or Chinese page
title — or a single curly quote — used to raise `UnicodeEncodeError` and take
the run down *after* the work was finished. The CLI now reconfigures its own
output to UTF-8 with replacement, so at worst a character prints as `?`.

The files on disk were never affected: every read and write in this package is
explicitly UTF-8, so `harvest.json` and `extract.json` hold the real text
whatever the console shows.

## What does *not* differ

- Paths — everything uses `pathlib`, so drive letters and backslashes are fine.
- Extraction, image metrics, contact sheets and chart reading — all pure Python
  plus Pillow, no external programs.
- Output — identical bytes to a Linux run, given the same rasterizer.

## Checklist when something fails

1. `python -m page_extract doctor` — it names every backend it looked for and
   the exact command to fix each one.
2. `python -m page_extract doctor --fix` — installs what pip can supply.
3. Still stuck on rasterizing? `--backend browser`, and set
   `PAGE_EXTRACT_BROWSER` if the browser is installed somewhere unusual.
