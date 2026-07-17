# awailly.github.io

Personal site of Aurélien Wailly (Senior Security Manager, Amazon). Static GitHub Pages site, pure HTML/CSS, no build step, no JS frameworks. Pushing to `master` deploys.

## Structure

- `index.html` — main page (bio, publications, lectures, projects, contact). All CSS is inline in a `<style>` block.
- `cours/index.html` — lectures page, mirrors the main page's design tokens.
- `favicon.svg` — source of truth for the icon: italic "a" with superscript "w" (aʷ, like a math exponent). All PNG/ICO variants are generated from it.
- `publications.xml` / `publications.xsl` — legacy publication data, no longer drives the page; publications are hand-maintained in `index.html`.
- `bootstrap/`, `fonts/`, `style.css` — dead legacy assets from the old Bootstrap 2 site, not loaded by any page.

## Design system (do not regress)

The fonts and design values were chosen by **measurement**, not taste — glyph geometry scored against legibility research optima (see git history around commit `44bc24b`):

- **Lora** — display: name, headings, publication titles (italic)
- **Public Sans** — body text, authors
- **Roboto Mono** — structural metadata: years, venue codes, nav, file links
- Colors: text `#313131` (13:1 contrast), secondary `#595959` (7:1), blue accent `#367195` (5.3:1, hue 203°), navy `#16213e`
- Type scale is geometric, ratio 1.34: body 1.0 → titles 1.34 → h2 1.79 → h1 2.4 rem
- Line-height 1.5, bio measures ~63 characters per line at 600px max-width
- Blue is informational (years, role, project names); avoid decorative color

Any change to fonts/colors/scale should keep WCAG AA minimum (4.5:1 for text) and preferably re-run the scoring approach rather than eyeballing.

## Favicon regeneration

After editing `favicon.svg`:

```sh
for s in 16 32 48 57 72 114 144 180 192 512; do
  rsvg-convert -w $s -h $s favicon.svg -o /tmp/fav$s.png
done
magick /tmp/fav16.png /tmp/fav32.png /tmp/fav48.png favicon.ico
cp favicon.ico assets/ico/favicon.ico
# then copy the PNGs to assets/ico/ under their existing names
```

Verify the 16px render is legible before committing (Read the PNG).

## Content rules

- **Writing style**: no em dashes, no AI-sounding filler. The bio is the owner's original wording; don't "improve" it.
- **Links**: only public URLs. OASC, SecSummit, and GameDay entries are internal Amazon venues — leave them unlinked. Dead conference sites get Internet Archive snapshots or ACM/IEEE/Springer records.
- **Publications**: venue abbreviation links to the conference/proceedings; `files` row links to local `/publications/*.pdf|.bib` where they exist.
- Lecture entries keep their institution logos (`img/brand/`) — students use them to find courses.

## Verifying changes

Screenshot locally before pushing:

```sh
python3 -m http.server 8765 &
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless \
  --screenshot=/tmp/site.png --window-size=1200,1400 --virtual-time-budget=8000 \
  http://localhost:8765
```

Ask before pushing unless told otherwise.
