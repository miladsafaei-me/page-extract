"""The command line. Every verb writes files and prints what it wrote."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .brand import Brand
from .errors import PageExtractError, RasterError

# What `doctor --fix` may install. Everything here is a normal PyPI wheel; the
# command never touches the system package manager, never asks for admin
# rights, and never installs outside the environment it is running in.
_FIXABLE = {"bs4": "beautifulsoup4", "lxml": "lxml", "PIL": "pillow",
            "cairosvg": "cairosvg"}


def _make_output_unicode_safe():
    """Stop a console encoding from destroying a finished run.

    A Windows console is cp1252 by default, so printing a page title in Persian,
    Turkish, or with nothing worse than a curly quote raises UnicodeEncodeError
    — after the work is already done. Reconfiguring once here covers every print
    in the package, and degrading a character beats losing the run.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass                                 # a pipe or a stream that cannot


def _pip_install(packages):
    """Install into the environment this tool is running in, never elsewhere."""
    print(f"\ninstalling: {' '.join(packages)}")
    # pip writes straight to the terminal, so anything still in our own buffer
    # would appear after it and read as though the order were reversed.
    sys.stdout.flush()
    return subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", *packages]).returncode


def _brand(args) -> Brand:
    if getattr(args, "brand", None):
        return Brand.load(args.brand)
    if getattr(args, "logo", None):
        return Brand.from_logo(args.logo)
    return Brand()


def cmd_doctor(args):
    from .raster import backends, find_browser, no_backend_message
    print(f"page-extract {__version__}   ·   python "
          f"{sys.version.split()[0]} on {sys.platform}\n")

    missing = []
    print("python packages")
    for mod in ("bs4", "lxml", "PIL"):
        try:
            __import__(mod)
            print(f"  [ok  ] {mod}")
        except ImportError:
            print(f"  [MISS] {mod}")
            missing.append(_FIXABLE[mod])

    print("\nSVG rasterizer  (needed only to write .webp; the .svg is always written)")
    rows = backends()
    for name, ok, detail in rows:
        print(f"  [{'ok  ' if ok else '--  '}] {name:13} {detail}")
    chosen = next((n for n, ok, _ in rows if ok), None)
    if chosen:
        print(f"\n  will use: {chosen}")
    else:
        print("\n  " + no_backend_message())
        if not find_browser():
            missing.append("cairosvg")

    if missing and args.fix:
        code = _pip_install(sorted(set(missing)))
        if code != 0:
            print("\npip failed — see its output above")
            return code
        print("\nre-checking...")
        sys.stdout.flush()
        return subprocess.run([sys.executable, "-m", "page_extract", "doctor"]).returncode

    if missing:
        print(f"\nmissing: {', '.join(sorted(set(missing)))}")
        print("run `page-extract doctor --fix` to install what pip can supply")
        return 1
    print("\nready")
    return 0


def cmd_harvest(args):
    from .extract import extract_url
    from .images import collect, contact_sheet
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"sources": {}, "gallery": [], "contact_sheet": None}
    gallery = []
    for i, url in enumerate(args.urls):
        sid = f"s{i + 1}"
        sdir = out / sid
        sdir.mkdir(exist_ok=True)
        try:
            doc = extract_url(url)
        except PageExtractError as exc:
            manifest["sources"][sid] = {"url": url, "error": str(exc)}
            print(f"  {sid} {url} -> {exc}")
            continue
        kept = collect(doc, out / "assets", label_prefix=f"{sid}-")
        for rec in kept:
            rec["label"] = f"{sid}#{rec['index']}"
            gallery.append(rec)
        doc.save(sdir / "extract.json")
        manifest["sources"][sid] = {
            "url": url, "title": doc.title, "word_count": doc.word_count,
            "headings": doc.headings, "tables": len(doc.tables),
            "images": len(doc.images), "kept_images": len(kept),
            "stat_sentences": len(doc.stat_sentences),
            "extract": str(sdir / "extract.json"),
        }
        print(f"  {sid} {url} -> {doc.word_count} words, "
              f"{len(doc.tables)} tables, {len(kept)}/{len(doc.images)} images kept")
    if gallery:
        sheet = out / "contact-sheet.jpg"
        size = contact_sheet(gallery, sheet)
        manifest["contact_sheet"] = str(sheet)
        manifest["gallery"] = [
            {"label": g["label"], "kind": g["kind"], "alt": g["alt"],
             "local": g["local"], "metrics": g.get("metrics", {})} for g in gallery]
        print(f"  contact sheet: {sheet} {size[0]}x{size[1]} "
              f"({len(gallery)} visuals from {len(args.urls)} sources)")
    (out / "harvest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {out / 'harvest.json'}")
    return 0


def cmd_chart(args):
    from .chartocr import preview, read, rescale, save
    bounds = tuple(int(v) for v in args.bounds.split(",")) if args.bounds else None
    series = read(args.image, bounds)
    if args.low is not None and args.high is not None:
        series = rescale(series, args.low, args.high, args.decimals)
    dest = Path(args.out or (str(args.image) + ".series.json"))
    save(series, dest)
    print(f"{len(series)} candles -> {dest}")
    if args.preview:
        preview(read(args.image, bounds), args.preview)
        print(f"preview -> {args.preview}  (compare it against the screenshot)")
    return 0


def cmd_figure(args):
    from . import figures
    from .raster import svg_to_webp
    params = json.loads(Path(args.params).read_text(encoding="utf-8")
                        if Path(args.params).exists() else args.params)
    svg = figures.build(args.builder, _brand(args), params)
    svg_path = Path(args.out).with_suffix(".svg")
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg, encoding="utf-8")
    print(svg_path)
    try:
        webp, size = svg_to_webp(svg_path, Path(args.out).with_suffix(".webp"),
                                 args.width, backend=args.backend)
    except RasterError as exc:
        # The drawing succeeded; only the raster step did not. Losing the SVG
        # too would throw away the work and hide which half actually broke.
        print(f"\nSVG written, WebP not: {exc}", file=sys.stderr)
        return 3
    print(f"{webp}  {size[0]}x{size[1]}")
    return 0


def cmd_builders(args):
    from . import figures
    for name, when in figures.describe().items():
        mod = figures.BUILDERS[name]
        print(f"\n## {name}")
        print(f"   {when}")
        print(f"   params: {json.dumps(mod.SCHEMA)}")
    return 0


def cmd_policy(args):
    from .policy import decide, explain
    if not args.shape:
        print(explain())
        return 0
    d = decide(args.shape, rows=args.rows, interactive=args.interactive,
               needs_reflow=not args.no_reflow, has_component=not args.no_component)
    print(d)
    return 0


def main(argv=None):
    _make_output_unicode_safe()
    ap = argparse.ArgumentParser(
        prog="page-extract",
        description="Turn a web page into a folder: substance as data, visuals "
                    "measured, and the ones worth keeping redrawn in your brand.")
    ap.add_argument("--version", action="version", version=f"page-extract {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("doctor", help="Check requirements and report what is missing.")
    d.add_argument("--fix", action="store_true",
                   help="pip-install whatever is missing, into this environment.")
    d.set_defaults(func=cmd_doctor)

    h = sub.add_parser("harvest", help="Fetch pages, extract them, measure and sheet "
                                       "their images.")
    h.add_argument("urls", nargs="+")
    h.add_argument("--out", required=True, help="Workspace directory.")
    h.set_defaults(func=cmd_harvest)

    c = sub.add_parser("chart", help="Recover an OHLC series from a chart screenshot.")
    c.add_argument("image")
    c.add_argument("--bounds", help="x0,y0,x1,y1 plot area, to exclude chrome.")
    c.add_argument("--low", type=float, help="Price at the bottom of the axis.")
    c.add_argument("--high", type=float, help="Price at the top of the axis.")
    c.add_argument("--decimals", type=int, default=2)
    c.add_argument("--out")
    c.add_argument("--preview", help="Write a redrawn PNG to compare against the source.")
    c.set_defaults(func=cmd_chart)

    f = sub.add_parser("figure", help="Draw a figure and rasterize it to WebP.")
    f.add_argument("builder")
    f.add_argument("params", help="A JSON file, or inline JSON.")
    f.add_argument("--out", required=True, help="Output path without extension.")
    f.add_argument("--brand", help="Brand JSON file.")
    f.add_argument("--logo", help="Logo SVG, if you have no brand file yet.")
    f.add_argument("--width", type=int, default=1200)
    f.add_argument("--backend", choices=("rsvg-convert", "cairosvg", "browser"),
                   help="Force one rasterizer instead of the best available.")
    f.set_defaults(func=cmd_figure)

    b = sub.add_parser("builders", help="List figure builders and when to pick each.")
    b.set_defaults(func=cmd_builders)

    p = sub.add_parser("policy", help="Markup or picture? Ask, or print the rule.")
    p.add_argument("shape", nargs="?")
    p.add_argument("--rows", type=int, default=0)
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--no-reflow", action="store_true")
    p.add_argument("--no-component", action="store_true")
    p.set_defaults(func=cmd_policy)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except PageExtractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
