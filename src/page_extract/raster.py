"""SVG to PNG and WebP, on whatever the machine actually has.

Rasterizing SVG is the one job in this package that needs something outside
pip, and the options differ sharply by platform. So rather than demand one
tool, this tries three in order and tells you which it used:

1. **rsvg-convert** — one package on any Linux, fastest, exact.
2. **cairosvg** — a pip install, but only where a cairo library already exists,
   which in practice means Linux and macOS.
3. **A headless browser** — Chrome, Edge, Chromium or Brave. Slower to start,
   perfect fidelity, and the reason this package works on Windows out of the
   box: Edge ships with Windows, so there is nothing to install at all.

If none is present the SVG is still written; only the raster step is lost.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .errors import RasterError

#: Executables to try, in preference order, plus the fixed install locations
#: Windows and macOS use — a browser is routinely installed without being on
#: PATH, and refusing to look there is what makes a tool "not work on Windows".
_BROWSER_NAMES = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable",
                  "chrome", "msedge", "microsoft-edge", "brave-browser")
_BROWSER_PATHS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
)

#: An explicit override always wins. A browser installed somewhere unusual is
#: the commonest reason discovery fails, and on Windows it is normal.
if os.environ.get("PAGE_EXTRACT_BROWSER"):
    _BROWSER_PATHS = (os.environ["PAGE_EXTRACT_BROWSER"],) + _BROWSER_PATHS

_SIZE_RE = re.compile(r'<svg[^>]*?\bwidth="(\d+(?:\.\d+)?)"[^>]*?\bheight="(\d+(?:\.\d+)?)"')
_VIEWBOX_RE = re.compile(r'<svg[^>]*?viewBox="[\d.\-]+\s+[\d.\-]+\s+([\d.]+)\s+([\d.]+)"')


def find_browser() -> str | None:
    for name in _BROWSER_NAMES:
        found = shutil.which(name)
        if found:
            return found
    for path in _BROWSER_PATHS:
        if Path(path).exists():
            return path
    return None


def backends() -> list[tuple[str, bool, str]]:
    """``(name, available, detail)`` for each backend, in preference order."""
    rows = []

    rsvg = shutil.which("rsvg-convert")
    rows.append(("rsvg-convert", bool(rsvg),
                 rsvg or "not installed — dnf install librsvg2-tools / "
                         "apt install librsvg2-bin / brew install librsvg"))

    try:
        import cairosvg                                        # noqa: F401
        rows.append(("cairosvg", True, "importable"))
    except Exception as exc:                                   # ImportError, or an OSError
        rows.append(("cairosvg", False,                        # when libcairo is absent
                     f"not usable ({type(exc).__name__}) — pip install "
                     '"page-extract[cairo]"; needs a cairo library, which '
                     "Windows does not ship"))

    browser = find_browser()
    rows.append(("browser", bool(browser),
                 browser or "no Chrome, Edge, Chromium or Brave found"))
    return rows


def available() -> str | None:
    """Name of the backend that will be used, or None if there is none."""
    for name, ok, _ in backends():
        if ok:
            return name
    return None


def _svg_size(svg_path: Path) -> tuple[int, int] | None:
    head = svg_path.read_text(encoding="utf-8", errors="replace")[:2000]
    for pattern in (_SIZE_RE, _VIEWBOX_RE):
        m = pattern.search(head)
        if m:
            return int(float(m.group(1))), int(float(m.group(2)))
    return None


def _browser_png(browser: str, svg_path: Path, png_path: Path, width=None) -> None:
    size = _svg_size(svg_path)
    if size is None:
        raise RasterError(f"{svg_path.name} declares no width/height or viewBox, "
                          "so the browser backend cannot size the page")
    w, h = size
    scale = (width / w) if width else 1.0
    # A private profile dir keeps the run from touching (or waiting on) the
    # user's real browser session, which on Windows is the usual cause of a
    # headless run that silently produces nothing.
    with tempfile.TemporaryDirectory(prefix="pgx-browser-") as profile:
        cmd = [browser, "--headless", "--disable-gpu", "--hide-scrollbars",
               "--no-sandbox", f"--user-data-dir={profile}",
               f"--force-device-scale-factor={scale:g}",
               f"--window-size={w},{h}",
               f"--screenshot={png_path}", svg_path.resolve().as_uri()]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not png_path.exists():
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        tail = detail[-1] if detail else f"exit code {proc.returncode}"
        raise RasterError(f"{Path(browser).name} produced no image: {tail}")


def svg_to_png(svg_path, png_path, width=None, backend=None) -> Path:
    """Rasterize an SVG. ``backend`` forces one; otherwise the best available."""
    svg_path, png_path = Path(svg_path), Path(png_path)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    chosen = backend or available()

    if chosen == "rsvg-convert":
        cmd = ["rsvg-convert", str(svg_path), "-o", str(png_path)]
        if width:
            cmd[1:1] = ["-w", str(width)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RasterError(f"rsvg-convert failed: {proc.stderr.strip()}")
    elif chosen == "cairosvg":
        import cairosvg
        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=width)
    elif chosen == "browser":
        browser = find_browser()
        if not browser:
            raise RasterError("the browser backend was requested but none was found")
        _browser_png(browser, svg_path, png_path, width)
    else:
        raise RasterError(no_backend_message())
    return png_path


def svg_to_webp(svg_path, webp_path, width=None, quality=88, keep_png=False,
                backend=None):
    """Render an SVG straight to WebP — the format a figure ships in."""
    from PIL import Image
    svg_path, webp_path = Path(svg_path), Path(webp_path)
    png_path = webp_path.with_suffix(".png")
    svg_to_png(svg_path, png_path, width, backend)
    im = Image.open(png_path).convert("RGB")
    im.save(webp_path, "WEBP", quality=quality, method=6)
    if not keep_png:
        png_path.unlink(missing_ok=True)
    return webp_path, im.size


def no_backend_message() -> str:
    """What to actually do, on the platform this is running on."""
    if sys.platform.startswith("win"):
        how = ("Install Microsoft Edge or Google Chrome — Edge ships with Windows, "
               "so this normally means it is installed somewhere unusual. Point at "
               "it with PAGE_EXTRACT_BROWSER=C:\\path\\to\\msedge.exe.")
    elif sys.platform == "darwin":
        how = ("brew install librsvg, or install Google Chrome — either is enough.")
    else:
        how = ("dnf install librsvg2-tools (or apt install librsvg2-bin), "
               'or pip install "page-extract[cairo]", or install Chromium.')
    return ("no SVG rasterizer found, so the WebP could not be written "
            f"(the SVG itself was still produced). {how} "
            "Run `page-extract doctor` to see what was looked for.")
