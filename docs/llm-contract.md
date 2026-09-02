# The seam: what a model should and should not see

This package exists to make the expensive part small. Everything it does is
deterministic; a language model is worth paying for exactly two things, and it
should never be handed the rest.

## Never hand a model

- **Raw HTML.** A 500 KB page is about 4 KB of substance. `extract.json` is that
  4 KB. Passing the page instead costs roughly a hundred times more and produces
  a worse answer, because the model has to find the article before it can think
  about it.
- **Images one at a time.** Fourteen separate images cost roughly ten times what
  one contact sheet costs, and are harder to compare. Look at the sheet.
- **A chart, to read its numbers.** `page-extract chart` recovers the series from
  pixels. A model asked to read prices off a chart will invent plausible ones,
  and you will not be able to tell.
- **A figure, to draw it.** Builders draw from parameters. A model writing raw
  SVG produces something that neither matches your brand nor survives review.

## Do hand a model

### 1. Classifying the visuals

Show the contact sheet **once**, with the `harvest.json` gallery listing beside
it. Ask for, per visual: what it *does*, and whether it is worth keeping.

The vocabulary matters. Ask for shapes — "hub with four spokes", "7x3
comparison", "candlestick chart with an entry annotation" — and explicitly *not*
for a component id or a builder name. Naming the production vehicle at this
stage is how a plan ends up reproducing the source's choices instead of making
its own.

### 2. Deciding what the destination needs

This is the judgment the package cannot make: which visuals your piece actually
wants, and which of those the source happens to have something useful for.

**Run it in that order, and the order is the whole point.** Decide what the
destination needs *first*, from the destination's own outline. Only then look at
what the source had, and take from it where the two coincide. Reversed — look at
the source, then decide — the source's visual choices become your outline, and
you have reproduced a competitor's article with better styling. That is a worse
outcome than having no source at all, because it feels like work.

A source visual earns a place only if it answers a need you had already written
down. Everything else on the sheet is discarded, however good it looks.

## The prompt shape that works

```
Here is the outline of the article we are writing:  <destination outline>
Here are the visual jobs it needs:                  <written before looking>
Here is what the sources happened to have:          <contact sheet + gallery>

For each visual job, say whether a source visual covers it. If none does, the
job stands on its own and we draw it from scratch. Never add a job because a
source had a nice picture for it.
```

## Cost, measured

On a 4,549-word page carrying 19 images, one real run:

| Stage | Approach | Relative cost |
|---|---|---|
| Understand the page | `extract.json` vs raw HTML | ~1x vs ~100x |
| Classify 14 visuals | one contact sheet vs 14 images | ~1x vs ~10x |
| Read a chart's numbers | `chartocr` vs a vision call | 0 vs ~1x, and correct |
| Draw a figure | builder + params vs generated SVG | ~0.05x, and on-brand |

The two stages left for the model — classification and the destination's own
visual plan — are small, and both genuinely need judgment.
