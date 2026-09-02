"""Getting bytes off the web, with the two behaviours every scraper needs:
a browser-shaped User-Agent, and a retry that does not hammer a slow host."""
from __future__ import annotations

import time
import urllib.error
import urllib.request
from pathlib import Path

from .errors import FetchError

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def get(url: str, timeout: int = 40, retries: int = 2, headers: dict | None = None) -> bytes:
    last = None
    req_headers = {"User-Agent": UA, "Accept-Language": "en;q=0.9"}
    req_headers.update(headers or {})
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            last = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise FetchError(f"could not fetch {url}: {last}")


def get_text(url: str, **kw) -> str:
    return get(url, **kw).decode("utf-8", errors="replace")


def download(url: str, dest, **kw) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(get(url, **kw))
    return dest
