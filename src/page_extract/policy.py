"""Should this visual ship as live markup, or as a drawn picture?

Rebuilding every source visual as HTML is a mistake, and so is rebuilding every
one as an image. The two formats fail in opposite directions:

*Live markup* (a component in the page) wins when the reader does something with
the visual — sorts it, hovers it, expands it — or when it must reflow to fit a
phone. Text stays selectable, translatable and readable by search engines, and
the thing restyles itself when the site's theme changes.

*A drawn picture* (SVG rasterized to WebP) wins when the layout **is** the
information: a hub with its parts around it, a process whose arrows cross, a 2x2
whose meaning is which quadrant a case lands in. Flattening those into stacked
markup does not just look worse, it deletes the relationship the visual existed
to show. Pictures also survive where markup does not — RSS, email, an OG card.

The rule below is a default, not a verdict. It answers from the shape of the
job, and a caller who knows better overrides it — `decide()` always says why, so
disagreeing with it is a decision rather than an accident.
"""
from __future__ import annotations

from dataclasses import dataclass

COMPONENT = "component"
FIGURE = "figure"

#: Shapes whose meaning is carried by where things sit relative to each other.
SPATIAL_SHAPES = {"hub_spokes", "radial", "cycle", "quadrant", "matrix_2x2",
                  "process_chain", "flow", "pyramid", "venn", "anatomy",
                  "annotated_diagram", "contrast_table"}

#: Shapes the reader operates, or that must reflow to stay readable.
INTERACTIVE_SHAPES = {"table", "comparison", "faq", "accordion", "calculator",
                      "decision_tree", "timeline", "checklist", "quiz",
                      "price_chart", "candles", "line_chart", "bar_chart",
                      "payoff", "stat_cards", "kpi"}


@dataclass
class Decision:
    format: str
    reason: str
    builder: str | None = None

    def __str__(self):
        where = f" ({self.builder})" if self.builder else ""
        return f"{self.format}{where}: {self.reason}"


def decide(shape: str, *, rows: int = 0, interactive: bool = False,
           needs_reflow: bool = True, has_component: bool = True) -> Decision:
    """Pick a format for one visual job.

    `shape` is what the visual *does* — "hub_spokes", "table", "price_chart" —
    never a component id from some catalog. Keeping the vocabulary at that level
    is what lets the same job be answered by a different catalog in a different
    project.
    """
    shape = (shape or "").strip().lower()

    if interactive:
        return Decision(COMPONENT, "the reader operates it, which a picture cannot support")

    if shape in INTERACTIVE_SHAPES:
        if shape in ("table", "comparison") and rows and rows <= 4 and not needs_reflow:
            return Decision(FIGURE, f"only {rows} rows and no reflow requirement, "
                                    "so the drawn version reads better",
                            builder="contrast_table")
        return Decision(COMPONENT,
                        "its content is data the reader scans, sorts or reads on a phone")

    if shape in SPATIAL_SHAPES:
        if not has_component:
            return Decision(FIGURE, "the layout carries the meaning and no component "
                                    "reproduces it", builder=shape if shape in
                            {"hub_spokes", "quadrant", "process_chain", "contrast_table"}
                            else None)
        return Decision(FIGURE, "position is the information here — stacking it into "
                                "markup would delete the relationship it shows",
                        builder=shape if shape in
                        {"hub_spokes", "quadrant", "process_chain", "contrast_table"}
                        else None)

    if not has_component:
        return Decision(FIGURE, "nothing in the catalog covers this shape")
    return Decision(COMPONENT, "no reason to flatten it into pixels")


def explain() -> str:
    """The rule in one paragraph, for a brief or a prompt."""
    return (
        "Ship a visual as live markup when the reader operates it or it must "
        "reflow — tables, charts, FAQs, calculators, decision trees. Ship it as a "
        "drawn SVG rasterized to WebP when the layout is the information — a hub "
        "and its parts, a process whose arrows cross, a 2x2 read by quadrant, a "
        "two-column contrast. When both would work, prefer markup: it stays "
        "selectable, translatable and themeable."
    )
