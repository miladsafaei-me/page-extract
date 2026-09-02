"""page-extract — turn a web page into a folder you can build from.

    from page_extract import extract_url, Brand, figures, raster

    doc = extract_url("https://example.com/article")
    svg = figures.build("hub_spokes", Brand.from_logo("logo.svg"), {...})
    raster.svg_to_webp("fig.svg", "fig.webp", width=1200)

It has no opinion about what you do with the result: no CMS, no database, no
publishing step, no content model. See docs/usage.md.
"""
from .brand import Brand
from .errors import (BrandError, ExtractionError, FetchError, PageExtractError,
                     RasterError)
from .extract import Document, extract, extract_url
from .policy import COMPONENT, FIGURE, decide

__version__ = "0.1.0"
__all__ = [
    "Brand", "Document", "extract", "extract_url", "decide", "COMPONENT", "FIGURE",
    "PageExtractError", "FetchError", "ExtractionError", "RasterError", "BrandError",
]
