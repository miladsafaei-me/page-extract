"""Tests that need no network: everything here runs on fixtures built in-process."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from page_extract import Brand, decide, extract                      # noqa: E402
from page_extract.brand import BrandError                            # noqa: E402
from page_extract.chartocr import group, read, rescale, scan, to_ohlc  # noqa: E402
from page_extract.extract import classify_image                      # noqa: E402
from page_extract.figures import BUILDERS, build                     # noqa: E402
from page_extract.images import contact_sheet, metrics, refine_kind  # noqa: E402
from page_extract.policy import COMPONENT, FIGURE                    # noqa: E402
from page_extract import svgkit as K                                 # noqa: E402

PAGE = """
<html><head><title>Widgets Compared</title>
<meta name="description" content="A comparison."></head><body>
<nav class="menu">nav junk</nav>
<article>
  <h1>Widgets Compared</h1>
  <p>Widgets come in two shapes and the difference matters more than it looks.
     One is fixed at the moment you buy it; the other keeps moving until you sell.</p>
  <p>That single difference drives everything below: what you pay, what you can
     do afterwards, and who you complain to when it goes wrong.</p>
  <h2>The numbers</h2>
  <p>Returns land between 70% and 85%, and fees run about $12 per lot.</p>
  <table><tr><th>Metric</th><th>A</th><th>B</th></tr>
         <tr><td>Cost</td><td>10</td><td>20</td></tr>
         <tr><td>Speed</td><td>3</td><td>9</td></tr></table>
  <img src="/img/chart-eurusd.png" alt="EURUSD chart" width="800" height="400">
  <img src="/img/site-logo.svg" alt="Logo" width="40" height="40">
  <figure><img src="/img/flow-diagram.png" alt="How it flows" width="900" height="500">
          <figcaption>The flow.</figcaption></figure>
</article>
<footer class="social">footer junk</footer></body></html>
"""


@pytest.fixture
def doc():
    return extract("https://example.com/a", PAGE)


def test_extract_finds_the_article_and_drops_chrome(doc):
    assert doc.title == "Widgets Compared"
    assert doc.meta_description == "A comparison."
    text = " ".join(b.get("text", "") for b in doc.blocks)
    assert "nav junk" not in text and "footer junk" not in text
    assert "The numbers" in doc.headings


def test_extract_reads_a_table_as_data(doc):
    assert len(doc.tables) == 1
    t = doc.tables[0]
    assert t["header"] == ["Metric", "A", "B"]
    assert t["shape"] == [2, 3]
    assert t["numeric_columns"] == [1, 2]


def test_extract_collects_stat_sentences(doc):
    assert doc.stat_sentences, "a sentence with 70%, 85% and $12 should be caught"
    assert "70%" in doc.stat_sentences[0]["text"]


def test_extract_resolves_and_classifies_images(doc):
    by_alt = {i["alt"]: i for i in doc.images}
    assert by_alt["EURUSD chart"]["src"] == "https://example.com/img/chart-eurusd.png"
    assert by_alt["EURUSD chart"]["kind"] == "chart"
    assert by_alt["Logo"]["kind"] == "chrome"
    assert by_alt["How it flows"]["caption"] == "The flow."


def test_classify_image_uses_size_for_chrome():
    assert classify_image("/x/thing.png", "thing", 40, 40) == "chrome"
    assert classify_image("/x/wide.png", "banner", 1200, 200) == "banner"


def test_extract_raises_on_a_page_with_no_article():
    with pytest.raises(Exception):
        extract("https://example.com/x", "<html><body><p>hi</p></body></html>")


# --- brand -----------------------------------------------------------------

def test_brand_defaults_merge_with_overrides():
    b = Brand(palette={"accent": "#123456"})
    assert b.color("accent") == "#123456"
    assert b.color("paper") == "#FFFFFF", "unspecified keys keep the default"


def test_brand_rejects_a_bad_corner():
    with pytest.raises(BrandError):
        Brand(watermark_corner="middle")


def test_brand_reports_an_unknown_colour_by_name():
    with pytest.raises(BrandError) as exc:
        Brand().color("puce")
    assert "puce" in str(exc.value)


def test_brand_round_trips_through_a_file(tmp_path):
    logo = tmp_path / "logo.svg"
    logo.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40">'
                    '<style>.a{fill: #00FF99;}</style><rect class="a" width="100" height="40"/></svg>')
    (tmp_path / "brand.json").write_text(json.dumps({
        "name": "Acme", "logo": "logo.svg", "watermark_corner": "bottom-left",
        "palette": {"ink": "#000000"}}))
    b = Brand.load(tmp_path / "brand.json")
    assert b.name == "Acme" and b.watermark_corner == "bottom-left"
    assert b.logo.name == "logo.svg" and b.color("ink") == "#000000"


def test_brand_from_logo_picks_up_the_mark_colour(tmp_path):
    logo = tmp_path / "l.svg"
    logo.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 4">'
                    '<style>.s{fill: #ABCDEF;}</style><rect class="s"/></svg>')
    assert Brand.from_logo(logo).color("accent") == "#ABCDEF"


# --- svg kit ---------------------------------------------------------------

def test_text_is_escaped():
    out = K.text(Brand(), 0, 0, 'a & b < c "q"')
    assert "&amp;" in out and "&lt;" in out and "&quot;" in out
    assert "<c" not in out


def test_wrap_never_drops_a_word():
    words = ["alpha", "beta", "gamma", "delta", "epsilon"]
    assert " ".join(K.wrap(" ".join(words), 12)).split() == words


def test_wrap_keeps_an_overlong_word_on_its_own_line():
    assert K.wrap("supercalifragilistic", 5) == ["supercalifragilistic"]


def test_watermark_is_empty_without_a_logo():
    assert K.watermark(Brand(), 100, 100) == ""


# --- figures ---------------------------------------------------------------

CASES = {
    "contrast_table": {"title": "T", "left_title": "A", "right_title": "B",
                       "rows": [{"label": "x", "left": "l", "right": "r"},
                                {"label": "y", "left": "l", "right": "r"}]},
    "hub_spokes": {"hub": "Core", "spokes": [{"label": "one"}, {"label": "two"},
                                             {"label": "three"}]},
    "process_chain": {"steps": [{"label": "a"}, {"label": "b"}, {"label": "c"}]},
    "quadrant": {"x_axis": {"label": "x", "low": "lo", "high": "hi"},
                 "y_axis": {"label": "y", "low": "lo", "high": "hi"},
                 "cells": [{"at": a, "label": a} for a in ("tl", "tr", "bl", "br")]},
}


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_every_builder_produces_one_well_formed_svg(name):
    from xml.etree import ElementTree
    svg = build(name, Brand(), CASES[name])
    ElementTree.fromstring(svg)                     # raises if malformed
    assert svg.startswith("<svg") and svg.endswith("</svg>")


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_every_builder_documents_when_to_pick_it(name):
    assert BUILDERS[name].WHEN_TO_PICK.strip()
    assert BUILDERS[name].SCHEMA


def test_unknown_builder_names_the_ones_that_exist():
    with pytest.raises(KeyError) as exc:
        build("nope", Brand(), {})
    assert "hub_spokes" in str(exc.value)


def test_hub_spokes_needs_three_spokes():
    with pytest.raises(ValueError):
        build("hub_spokes", Brand(), {"hub": "h", "spokes": [{"label": "a"}]})


# --- policy ----------------------------------------------------------------

def test_spatial_shapes_become_pictures():
    assert decide("hub_spokes").format == FIGURE
    assert decide("quadrant").builder == "quadrant"


def test_operable_shapes_stay_markup():
    assert decide("price_chart").format == COMPONENT
    assert decide("faq").format == COMPONENT
    assert decide("hub_spokes", interactive=True).format == COMPONENT


def test_a_small_static_table_is_drawn_instead():
    assert decide("table", rows=7).format == COMPONENT
    d = decide("table", rows=3, needs_reflow=False)
    assert d.format == FIGURE and d.builder == "contrast_table"


def test_every_decision_carries_a_reason():
    for shape in ("hub_spokes", "table", "mystery", "quadrant"):
        assert decide(shape).reason


# --- chart ocr -------------------------------------------------------------

def _chart(path, bars):
    """Draw a candle chart, so the reader is tested against a known series."""
    im = Image.new("RGB", (40 * len(bars) + 40, 400), "white")
    d = ImageDraw.Draw(im)
    for i, (o, h, low, c) in enumerate(bars):
        cx = 20 + 40 * i + 20
        color = "#22c55e" if c >= o else "#ef4444"
        d.line([(cx, 400 - h), (cx, 400 - low)], fill=color, width=3)
        d.rectangle([cx - 12, 400 - max(o, c), cx + 12, 400 - min(o, c)], fill=color)
    im.save(path)
    return im


def test_chart_reader_recovers_the_right_number_of_candles(tmp_path):
    bars = [(100, 180, 90, 160), (160, 200, 150, 155), (155, 190, 120, 130),
            (130, 240, 125, 230), (230, 260, 200, 210)]
    p = tmp_path / "c.png"
    _chart(p, bars)
    series = read(p)
    assert len(series) == len(bars)


def test_chart_reader_preserves_direction(tmp_path):
    bars = [(100, 180, 90, 170), (170, 175, 100, 110)]
    p = tmp_path / "c.png"
    _chart(p, bars)
    series = read(p)
    assert series[0]["c"] > series[0]["o"], "first bar was bullish"
    assert series[1]["c"] < series[1]["o"], "second bar was bearish"


def test_chart_reader_normalizes_to_the_unit_range(tmp_path):
    p = tmp_path / "c.png"
    _chart(p, [(100, 180, 90, 160), (160, 250, 150, 240), (240, 260, 200, 210)])
    series = read(p)
    lows = [s["l"] for s in series]
    highs = [s["h"] for s in series]
    assert min(lows) == pytest.approx(0.0, abs=0.02)
    assert max(highs) == pytest.approx(1.0, abs=0.02)


def test_rescale_maps_onto_a_real_axis():
    out = rescale([{"o": 0.0, "h": 1.0, "l": 0.0, "c": 0.5}], 100, 200)
    assert out[0] == {"o": 100.0, "h": 200.0, "l": 100.0, "c": 150.0}


def test_empty_image_yields_no_candles(tmp_path):
    p = tmp_path / "blank.png"
    Image.new("RGB", (200, 200), "white").save(p)
    assert read(p) == []


# --- images ----------------------------------------------------------------

def test_metrics_separate_flat_art_from_a_noisy_field(tmp_path):
    flat = tmp_path / "flat.png"
    Image.new("RGB", (300, 200), "#eef2ff").save(flat)
    assert metrics(flat)["flat_share"] > 0.9

    import random
    noisy = tmp_path / "noisy.png"
    im = Image.new("RGB", (300, 200))
    rnd = random.Random(0)
    im.putdata([(rnd.randrange(256), rnd.randrange(256), rnd.randrange(256))
                for _ in range(300 * 200)])
    im.save(noisy)
    assert metrics(noisy)["flat_share"] < 0.1


def test_refine_kind_never_promotes_chrome():
    assert refine_kind("chrome", {"flat_share": 0.9, "edge_density": 0.5,
                                  "distinct_colors": 3}) == "chrome"


def test_contact_sheet_lays_every_image_out(tmp_path):
    recs = []
    for i in range(5):
        p = tmp_path / f"{i}.png"
        Image.new("RGB", (400, 300), (i * 40, 90, 200)).save(p)
        recs.append({"local": str(p), "label": f"s1#{i}"})
    out = tmp_path / "sheet.jpg"
    w, h = contact_sheet(recs, out)
    assert out.exists()
    assert w == 470 * 4, "four columns"
    assert h > 300, "two rows for five images"


# --- portability -----------------------------------------------------------
# These pin the behaviours that made this unusable on Windows: no rasterizer to
# be found, console encodings that cannot hold the text, and a console script
# that is not on PATH.

def test_backends_are_reported_in_preference_order():
    from page_extract.raster import backends
    names = [n for n, _, _ in backends()]
    assert names == ["rsvg-convert", "cairosvg", "browser"]


def test_every_backend_row_explains_itself():
    from page_extract.raster import backends
    for name, ok, detail in backends():
        assert detail, f"{name} reported nothing"
        if not ok:
            assert len(detail) > 20, f"{name} does not say what to do about it"


def test_the_no_backend_message_names_a_platform_specific_fix(monkeypatch):
    from page_extract import raster
    for platform, expect in (("win32", "Edge"), ("darwin", "brew"), ("linux", "dnf")):
        monkeypatch.setattr(raster.sys, "platform", platform)
        assert expect in raster.no_backend_message()


def test_a_browser_override_is_searched_first(monkeypatch, tmp_path):
    exe = tmp_path / "msedge.exe"
    exe.write_text("")
    monkeypatch.setenv("PAGE_EXTRACT_BROWSER", str(exe))
    import importlib

    from page_extract import raster
    reloaded = importlib.reload(raster)
    try:
        assert str(exe) in reloaded._BROWSER_PATHS
    finally:
        monkeypatch.delenv("PAGE_EXTRACT_BROWSER")
        importlib.reload(raster)


def test_windows_and_mac_install_paths_are_searched():
    from page_extract.raster import _BROWSER_PATHS
    joined = " ".join(_BROWSER_PATHS)
    assert "msedge.exe" in joined, "Edge ships with Windows; not looking there is the bug"
    assert "chrome.exe" in joined
    assert "/Applications/" in joined


def test_svg_size_is_read_from_width_height_or_viewbox(tmp_path):
    from page_extract.raster import _svg_size
    a = tmp_path / "a.svg"
    a.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" '
                 'width="800" height="600"></svg>', encoding="utf-8")
    assert _svg_size(a) == (800, 600)
    b = tmp_path / "b.svg"
    b.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 480"></svg>',
                 encoding="utf-8")
    assert _svg_size(b) == (640, 480)
    c = tmp_path / "c.svg"
    c.write_text("<svg></svg>", encoding="utf-8")
    assert _svg_size(c) is None


def test_missing_rasterizer_raises_with_the_fix_in_the_message(tmp_path, monkeypatch):
    from page_extract import raster
    from page_extract.errors import RasterError
    monkeypatch.setattr(raster, "available", lambda: None)
    svg = tmp_path / "x.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>',
                   encoding="utf-8")
    with pytest.raises(RasterError) as exc:
        raster.svg_to_png(svg, tmp_path / "x.png")
    assert "SVG itself was still produced" in str(exc.value)


def test_the_figure_command_keeps_the_svg_when_rasterizing_fails(tmp_path, capsys):
    from page_extract.cli import main
    out = tmp_path / "fig"
    code = main(["figure", "hub_spokes",
                 json.dumps({"hub": "H", "spokes": [{"label": "a"}, {"label": "b"},
                                                    {"label": "c"}]}),
                 "--out", str(out), "--backend", "browser"])
    assert code == 3, "a lost raster is not the same failure as a lost drawing"
    assert out.with_suffix(".svg").exists(), "the drawing must survive"
    assert not out.with_suffix(".webp").exists()


def test_output_is_made_unicode_safe_before_anything_prints(monkeypatch):
    """A cp1252 console must not be able to kill a finished run."""
    from page_extract.cli import _make_output_unicode_safe

    class Narrow:
        encoding = "cp1252"
        def __init__(self): self.called = None
        def reconfigure(self, **kw): self.called = kw

    out, err = Narrow(), Narrow()
    monkeypatch.setattr("sys.stdout", out)
    monkeypatch.setattr("sys.stderr", err)
    _make_output_unicode_safe()
    assert out.called == {"encoding": "utf-8", "errors": "replace"}
    assert err.called == {"encoding": "utf-8", "errors": "replace"}


def test_unicode_safety_tolerates_a_stream_that_cannot_reconfigure(monkeypatch):
    from page_extract.cli import _make_output_unicode_safe

    class Pipe:
        pass                                      # no reconfigure at all

    monkeypatch.setattr("sys.stdout", Pipe())
    monkeypatch.setattr("sys.stderr", Pipe())
    _make_output_unicode_safe()                   # must not raise


def test_the_module_entry_point_exists():
    """`python -m page_extract` is the way in when Scripts\\ is not on PATH."""
    import importlib.util
    from pathlib import Path as P
    import page_extract
    assert (P(page_extract.__file__).parent / "__main__.py").exists()


def test_doctor_runs_and_reports(capsys):
    from page_extract.cli import main
    main(["doctor"])
    out = capsys.readouterr().out
    assert "python packages" in out
    assert "SVG rasterizer" in out
    for backend in ("rsvg-convert", "cairosvg", "browser"):
        assert backend in out
