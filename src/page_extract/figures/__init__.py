"""Figure builders — the answer to "this one should not be HTML".

Some visuals belong in the page as live markup: anything the reader sorts,
hovers, expands or reads on a phone. Others are *drawings* — a hub with its
spokes, a process whose arrows cross, a 2x2 whose meaning is its position — and
turning those into markup produces a worse thing than a picture, because the
layout IS the information.

Each builder takes a `Brand` and a plain params dict and returns a complete SVG
string, watermarked. `page_extract.raster` turns that into the WebP that ships.

    from page_extract.figures import build, BUILDERS
    svg = build("hub_spokes", brand, {...})
"""
from __future__ import annotations

from . import contrast_table, hub_spokes, process_chain, quadrant

BUILDERS = {
    "contrast_table": contrast_table,
    "hub_spokes": hub_spokes,
    "process_chain": process_chain,
    "quadrant": quadrant,
}


def build(name: str, brand, params: dict) -> str:
    try:
        module = BUILDERS[name]
    except KeyError:
        raise KeyError(
            f"no figure builder {name!r}; have {sorted(BUILDERS)}") from None
    return module.build(brand, params)


def describe() -> dict[str, str]:
    """Builder name -> its one-line "reach for this when" note."""
    return {name: (mod.WHEN_TO_PICK or "").strip() for name, mod in BUILDERS.items()}
