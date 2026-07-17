# Design methodology

This site's typography and design values were not chosen by taste. Every font and
every design token (colors, type scale, line heights) was selected by measuring
candidates against research-backed optima and picking the highest scorer. This
document records the approach, the benchmarks, and the results so future changes
can be evaluated the same way.

## Principle

For each measurable property, define:

1. an **optimum** taken from typography and legibility research,
2. a **sigma** (tolerance) expressing how quickly quality degrades away from it,
3. a **weight** expressing how much the property matters for the role.

Each candidate gets a per-metric score via Gaussian falloff:

```
score = 100 * exp(-((value - optimum)^2) / (2 * sigma^2))
```

and a total as the weighted mean. This rewards being near the optimum on
everything over being perfect on one metric and poor on another.

## Font selection

### Metrics measured from the font binaries

Glyph geometry is extracted from the actual font files, two independent ways:

- **Outline analysis** (`measure_outline.py`): flattens the Bezier contours of
  glyphs (o, n, x, H, p) and intersects them with scanlines to measure stroke
  widths, counters, and heights in font units.
- **Raster analysis** (`measure_raster.py`): renders glyphs with FreeType at a
  512px em and measures the same properties from the monochrome bitmaps.

Both methods produced the same ranking for the metrics they shared, which
validates the measurements.

### Serif (display: name, headings, publication titles)

| Metric | What it captures | Optimum | Basis |
|---|---|---|---|
| x-height ratio (x/H) | small-size readability | 0.72 | Legge & Bigelow, book faces |
| stroke contrast (o thick/thin) | warmth vs. fatiguing sparkle | 2.5:1 | book-face norm; Didones ~6:1 are harsh |
| stem weight (n stem/em) | substance without bulk | 0.085 | text-face norm |
| width economy (avg advance/em) | reading rhythm | 0.50 | classic text faces |
| counter openness (o inner/outer) | letter recognition | 0.60 | aperture research |
| descender depth (/em) | rhythm and warmth | 0.25 | book-face norm |

Results (15 candidates from Google Fonts, outline method):

| Rank | Font | Score |
|---|---|---|
| 1 | **Lora** | **95.5** |
| 2 | Libre Baskerville | 93.5 |
| 3 | Fraunces | 93.2 |
| 4 | Crimson Pro | 90.7 |
| 5 | Newsreader | 79.8 |
| 6 | Bitter | 79.6 |
| 7 | Literata | 78.9 |
| 8 | Alegreya | 73.3 |
| 9 | Playfair Display | 70.5 (contrast 5.4:1 — display sparkle) |
| 10 | EB Garamond | 67.6 (x-height 0.615 — too small on screen) |
| 11 | Vollkorn | 67.0 |
| 12 | Source Serif 4 | 66.3 |
| 13 | Spectral | 46.7 |
| 14 | Cormorant Garamond | 45.9 |
| 15 | Cardo | 25.8 |

Lora won on the three heaviest metrics simultaneously: x-height 0.714,
contrast 2.88, counter 0.601.

### Sans (body text, author lists) — `measure_roles.py`

Optima shifted for screen body text: x-height 0.73, near-monolinear contrast
1.2, counter 0.62, descender 0.22.

| Rank | Font | Score |
|---|---|---|
| 1 | **Public Sans** | **98.0** |
| 2 | Inter | 94.6 |
| 3 | Figtree | 90.7 |
| 4 | Albert Sans | 89.5 |
| 5 | Work Sans | 88.1 |

### Monospace (metadata: years, venues, nav, file links)

Optima shifted for tiny label sizes: x-height 0.75 (weight 30), sturdier stems
0.09, tight descenders 0.22.

| Rank | Font | Score |
|---|---|---|
| 1 | **Roboto Mono** | **91.0** |
| 2 | Ubuntu Mono | 90.8 |
| 3 | IBM Plex Mono | 89.3 |
| 4 | Source Code Pro | 88.0 |
| 7 | JetBrains Mono | 75.8 (deep descenders; designed for editors, not labels) |

### Coherence check

The three winners have x-heights within 0.71-0.75 of cap height, so mixed lines
(serif title + mono year + sans authors) sit together without visual jumps.

## Design audit (`design_audit.py`)

The same scoring applied to the page itself. The script parses the CSS custom
properties and rules out of `index.html`, computes WCAG contrast from the real
hex values, and computes true characters-per-line from Lora's measured average
advance width (0.514 em) rather than a rule of thumb.

| Metric | Optimum | Basis |
|---|---|---|
| body text contrast | 13:1 | AAA (7:1) but below pure-black glare |
| secondary text contrast | 7:1 | WCAG AAA |
| accent-as-text contrast | >= 4.5:1 | WCAG AA hard floor |
| decorative (non-text) contrast | >= 3:1 | WCAG non-text |
| line length | 66 cpl | Bringhurst (45-75 acceptable) |
| line height | 1.5 | W3C readability |
| type scale consistency | geometric (CV of adjacent ratios = 0) | modular scale |
| accent hue relationship | 180 deg apart | complementary harmony |
| spacing rhythm | values on a 0.05rem grid | consistent rhythm |

### Before/after

The first audit scored **66.0/100** and localized every weakness:

| Metric | Before | After | Fix |
|---|---|---|---|
| body contrast | 14.0:1 | 13.0:1 | text `#2c2c2c` -> `#313131` |
| secondary contrast | 6.0:1 | 7.0:1 | `#636363` -> `#595959` |
| blue label contrast | 4.4:1 (WCAG fail) | 5.3:1 | `#3d7ea6` -> `#367195`, same hue 203 |
| body line-height | 1.75 | 1.5 | |
| bio line-height | 1.8 | 1.5 | |
| type scale | ratios 1.60/1.43/1.05 | 1.34/1.34/1.34 | geometric, ratio = cube root of 2.4 |
| line length | 63 cpl | 63 cpl | already near optimum |
| hue harmony | 174 deg | 174 deg | already near-complementary |

Final score: **99.3/100**.

## Reproducing

```sh
python3 -m venv fontenv
fontenv/bin/pip install fonttools brotli freetype-py numpy

# download candidates as woff2 into fonts/ (latin subset; see script comments),
# convert to ttf for the raster path, then:
fontenv/bin/python measure_outline.py   # serif scoring
fontenv/bin/python measure_roles.py     # sans + mono scoring (fonts/sans, fonts/mono)
fontenv/bin/python design_audit.py ../index.html
```

Note: Google Fonts serves character subsets; fetch the css2 endpoint with a
browser User-Agent and take the `/* latin */` block, or use the legacy
`fonts.googleapis.com/css?family=` endpoint with a non-browser UA to get full
TTFs (needed for advance-width measurements).

## Caveats

- The optima encode a specific goal: a warm, smooth, easy-reading academic
  page. A display-heavy or brutalist design would need different optima, not a
  different method.
- Stroke-contrast measurement on round glyphs is approximate (scanline placement
  matters); the two independent methods agreeing is the guard against artifacts.
- Scores compare candidates against each other under one model. 95.5 vs 93.5 is
  a real but small difference; 95.5 vs 45.9 is decisive.
