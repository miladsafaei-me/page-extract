"""Pull the article out of a page, as data rather than as markup.

The output is deliberately small: a caller (often a language model) should be
able to read the whole thing without ever seeing the 500 KB of HTML it came
from. That is most of the cost saving this package exists for.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .errors import ExtractionError

NOISE_TAGS = ["script", "style", "noscript", "nav", "header", "footer", "aside",
              "form", "iframe", "svg"]
NOISE_CLASS = re.compile(
    r"(share|social|breadcrumb|sidebar|related|comment|newsletter|subscribe|"
    r"advert|banner|cookie|menu|widget|toc|author-box|tag-list|pagination)", re.I)
STAT = re.compile(
    r"(\d+(?:\.\d+)?\s*%|[$€£]\s?\d[\d,]*(?:\.\d+)?|\b\d+(?:\.\d+)?\s*"
    r"(?:x|times|pips|bps|percent|billion|million|trillion|k)\b)", re.I)


@dataclass
class Document:
    url: str
    title: str = ""
    meta_description: str = ""
    word_count: int = 0
    blocks: list = field(default_factory=list)
    tables: list = field(default_factory=list)
    images: list = field(default_factory=list)
    stat_sentences: list = field(default_factory=list)

    @property
    def headings(self) -> list[str]:
        return [b["text"] for b in self.blocks if b["type"] in ("h2", "h3")]

    def to_json(self, indent=1) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=indent)

    def save(self, path) -> Path:
        path = Path(path)
        path.write_text(self.to_json(), encoding="utf-8")
        return path


#: Selector -> how much text it must hold to be believed. A page that used a
#: real <article> tag has told us where the article is, so it needs far less
#: corroboration than a div we guessed at by class name.
_ROOT_SELECTORS = (
    ("article", 120), ("main", 120),
    ("div.entry-content", 1200), ("div.post-content", 1200),
    ("div.article-content", 1200), ("div.article-body", 1200),
    ("div.content", 1200),
)


def _article_root(soup):
    for sel, floor in _ROOT_SELECTORS:
        node = soup.select_one(sel)
        if node and len(node.get_text(strip=True)) > floor:
            return node
    candidates = soup.find_all(["div", "section"])
    best = max(candidates, key=lambda n: len(n.get_text(strip=True)), default=None)
    if best is None or len(best.get_text(strip=True)) < 400:
        raise ExtractionError("no block of article-sized text found on the page")
    return best


def _strip_noise(root):
    """Drop the tags and the classed blocks that are page furniture, not article.

    Both loops walk a list that was materialised before any of it was removed, so
    a node can already have been destroyed by the time its turn comes -- a nav
    inside a wrapper whose class also matched, say. bs4 empties a decomposed
    node's ``attrs`` to ``None``, so touching one raises rather than being a
    harmless no-op, which is why every node is checked before it is read. A page
    with nested furniture used to crash the whole extraction here.
    """
    for sel in NOISE_TAGS:
        for node in root.select(sel):
            if not getattr(node, "decomposed", False):
                node.decompose()
    for node in root.find_all(attrs={"class": True}):
        if getattr(node, "decomposed", False) or not node.attrs:
            continue
        classes = node.get("class") or []
        if isinstance(classes, str):
            classes = classes.split()
        if NOISE_CLASS.search(" ".join(classes)):
            node.decompose()
    return root


def _table(node):
    rows = []
    for tr in node.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
        if any(cells):
            rows.append(cells)
    if len(rows) < 2:
        return None
    header, body = rows[0], rows[1:]
    numeric = []
    for i in range(len(header)):
        col = [r[i] for r in body if i < len(r)]
        if col and sum(1 for v in col if re.search(r"\d", v)) / len(col) >= 0.6:
            numeric.append(i)
    return {"header": header, "rows": body, "shape": [len(body), len(header)],
            "numeric_columns": numeric,
            "comparison_like": len(header) in (3, 4) and len(body) >= 3}


def classify_image(src, alt, width=0, height=0):
    """A first guess at what an image *is*, from its name, alt and size alone.

    Deliberately cheap and deliberately fallible — its job is to throw away
    chrome before anything expensive looks at the rest. `page_extract.images`
    refines it with pixel metrics; only a human or a model settles the rest.
    """
    text = f"{src} {alt}".lower()
    if re.search(r"(logo|icon|avatar|profile|badge|favicon|sprite)", text):
        return "chrome"
    if width and height and width < 120 and height < 120:
        return "chrome"
    if re.search(r"(chart|graph|candle|price|trend|plot|chartimg)", text):
        return "chart"
    if re.search(r"(infographic|infografi|diagram|flow|process|steps?)", text):
        return "infographic"
    if re.search(r"(screenshot|screen-|capture)", text):
        return "screenshot"
    ratio = (width / height) if (width and height) else None
    if ratio and ratio > 2.4:
        return "banner"
    return "unknown"


def extract(url: str, html: str) -> Document:
    soup = BeautifulSoup(html, "lxml")
    title = soup.find("title")
    desc = soup.find("meta", attrs={"name": "description"})
    root = _strip_noise(_article_root(soup))

    doc = Document(
        url=url,
        title=title.get_text(strip=True) if title else "",
        meta_description=(desc.get("content", "") if desc else ""),
    )
    seen = set()
    for node in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "table", "img", "figure"]):
        if node.name == "table":
            data = _table(node)
            if data:
                data["index"] = len(doc.tables)
                doc.tables.append(data)
                doc.blocks.append({"type": "table_ref", "index": data["index"]})
            continue
        if node.name in ("img", "figure"):
            img = node if node.name == "img" else node.find("img")
            if not img:
                continue
            src = (img.get("src") or img.get("data-src")
                   or img.get("data-lazy-src") or img.get("data-original") or "")
            if not src or src.startswith("data:"):
                continue
            src = urljoin(url, src)
            if src in seen:
                continue
            seen.add(src)
            try:
                w = int(img.get("width") or 0)
                h = int(img.get("height") or 0)
            except (TypeError, ValueError):
                w = h = 0
            cap = node.find("figcaption") if node.name == "figure" else None
            rec = {"index": len(doc.images), "src": src,
                   "alt": (img.get("alt") or "").strip(),
                   "caption": cap.get_text(" ", strip=True) if cap else "",
                   "width": w, "height": h,
                   "kind": classify_image(src, img.get("alt") or "", w, h)}
            doc.images.append(rec)
            doc.blocks.append({"type": "image_ref", "index": rec["index"]})
            continue

        text = node.get_text(" ", strip=True)
        if not text or len(text) < 3:
            continue
        if doc.blocks and doc.blocks[-1].get("text") == text:
            continue
        doc.blocks.append({"type": node.name, "text": text})
        if node.name in ("p", "li"):
            hits = STAT.findall(text)
            if len(hits) >= 2:
                doc.stat_sentences.append(
                    {"block": len(doc.blocks) - 1, "text": text, "hits": hits})

    doc.word_count = sum(len(b.get("text", "").split()) for b in doc.blocks)
    return doc


def extract_url(url: str, **fetch_kw) -> Document:
    from .fetch import get_text
    return extract(url, get_text(url, **fetch_kw))
