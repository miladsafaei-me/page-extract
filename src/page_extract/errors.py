"""Every failure this package raises, so a caller can catch one family."""


class PageExtractError(Exception):
    """Base class for everything below."""


class FetchError(PageExtractError):
    """The page could not be retrieved."""


class ExtractionError(PageExtractError):
    """The page was retrieved but no article could be found in it."""


class RasterError(PageExtractError):
    """No SVG rasterizer is available, or one failed."""


class BrandError(PageExtractError):
    """A brand file is missing, malformed, or names an asset that is not there."""
