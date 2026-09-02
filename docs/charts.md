# Reading a chart back out of a screenshot

A screenshot of a candlestick chart is data that was flattened into pixels.
Getting it back needs no model, because candles have three properties that make
them findable:

1. They are the only **strongly green or strongly red** things in the frame.
2. Each candle is a **contiguous vertical run** of coloured pixels.
3. The candle's **body** is its wide part; the **wick** is a thin centre line
   that extends past it.

## The passes

**Colour segmentation.** A pixel is bullish if green clearly dominates both red
and blue, bearish if red clearly dominates green and blue. Deliberately strict:
a muted grid line or a pale background tint fails both tests.

**Longest contiguous run per column.** This is what keeps legend swatches,
toolbar icons and axis ticks out. They are coloured, but they are not part of a
candle's vertical run, so the longest run in that column wins.

**Grouping into candles.** Adjacent coloured columns merge. Two corrections make
this survive real screenshots:

- *Pitch splitting.* Dark themes draw candles edge to edge with no gap, so
  contiguity alone under-segments. A run far wider than the modal candle is cut
  back into equal-pitch parts.
- *Outlier rejection.* Any candle taller than three times the median, or much
  wider than the modal width, is chrome that survived the crop. On a real chart
  no bar towers over its neighbours like that.

**Body vs wick.** Within a candle, columns no taller than ~1.6x the median are
the body; the full run gives high and low. Direction comes from which colour
dominated, which sets whether open is the body's top or its bottom.

**Normalization.** Output is 0-1 on the price axis, because pixels cannot know
what the axis said. `rescale(series, low, high)` maps it onto real numbers.

## Verify it, every time

```bash
page-extract chart shot.png --bounds 6,34,800,392 --preview check.png
```

`--preview` redraws the recovered series as its own image. Put it beside the
screenshot: the shapes either match or they do not. This takes a second and
tells you more than any amount of reading JSON.

## When it fails

| Symptom | Cause | Fix |
|---|---|---|
| Wild spikes at the edges | Toolbar or axis chrome inside the crop | Tighten `--bounds` |
| Too few candles, very wide | Dark theme, candles touching | Usually auto-split; crop tighter if not |
| No candles at all | Monochrome, hollow or line chart | Not supported — this reads filled candles |
| Series looks squashed | Log scale on the source axis | Geometry is right, the mapping is not linear |
| Colours inverted | A theme where red is up | Not detected; swap after `read()` |

## Honesty

The result is a **reconstruction**, accurate to a pixel of the original render,
not a market data feed. Say so where it is published. If you have your own price
data for the same instrument and window, prefer it — the reconstruction is for
when you do not.
