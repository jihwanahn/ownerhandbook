# Image rules — The Owner's Handbook

Every published guide carries at least one visual (two to three is the target). These
rules exist because AdSense review and copyright risk both live in the images, and
because a 3 MB hero photo destroys the page-speed budget the theme was built around.

## 1. Provenance — self-produced only

| Allowed | Not allowed |
| --- | --- |
| Diagrams and charts drawn by `build_samples.py` (SVG → WebP) | Stock photos (free or paid) |
| Illustrations generated in-house (`image_generate`) and captioned by `compose_caption.mjs` | Memes, screenshots or clip-art made by someone else |
| Screenshots of software the guide actually discusses, taken by us | Product photos lifted from a vendor's marketing site |
| Charts rendered from our own verified dataset | Anything whose licence we cannot point at |

If a licence cannot be named, the image does not ship.

## 2. Technical format

| Property | Rule | Enforced by |
| --- | --- | --- |
| Format | WebP | `optimize_images.py check` |
| Width | exactly 1200 px | `optimize_images.py check` |
| Weight | under 400 KB | `optimize_images.py check` |
| Filename | English kebab-case, e.g. `llc-filing-fee-breakdown.webp` | `optimize_images.py check` |
| Alt text | required, describes the content not the file | `md2blogger.py` quality gate |
| Caption | required on every `<figure>` | `md2blogger.py` quality gate |

## 3. Two house styles

1. **Explanatory (default)** — code-drawn SVG: bar charts, timelines, comparison
   tables. Deterministic, diffable, a few KB, and the numbers can be swapped the
   moment a source is verified. `python blogger/images/build_samples.py` regenerates
   both the `.svg` source and the `.webp` output.
2. **Humour (occasional)** — one illustration plus our own caption text:
   `node blogger/images/compose_caption.mjs in.jpg out.webp --top "…" --bottom "…"`.
   The illustration is generated in-house, the joke is written in-house, the file has
   no third-party pixels. Style B alternative: a pure-SVG two-panel joke
   (`helpful-relative-advice.webp`), which needs no generation step at all.

## 4. How images enter a guide

Author in markdown; the converter produces the Blogger HTML:

```markdown
![Average LLC filing fee by state, 2026](assets/images/llc-filing-fee-breakdown.webp "Filing fees cluster between $90 and $200.")
```

```html
<figure>
  <img src="https://<asset-host>/llc-filing-fee-breakdown.webp" alt="Average LLC filing fee by state, 2026" width="1200" loading="lazy" decoding="async"/>
  <figcaption>Filing fees cluster between $90 and $200.</figcaption>
</figure>
```

- A standalone `![alt](file "caption")` line becomes a `<figure>` with `<figcaption>`.
- `alt` is mandatory; the quoted string after the path is the caption and is also
  mandatory for a figure.
- The theme also injects `loading="lazy"` on images pasted straight into Blogger, so
  nothing above-the-fold blocking ever ships.

## 5. Hosting

Blogger's API has no image upload endpoint, so the body references absolute URLs.

- **Now (pre-GitHub):** images are stored in `assets/images/` in this repo and are not
  published. `md2blogger.py` refuses to emit payloads that still contain the
  `{{ASSET_BASE}}` placeholder, which is why a draft cannot be created with
  unpublished image URLs.
- **Phase 2 (planned):** the same files are served from GitHub Pages; set
  `assets.publicBaseUrl` in `blogger/config.json` once the host is connected (or pass
  `--assets-base` for a one-off run).

## 6. Commands

```bash
python blogger/images/build_samples.py                 # redraw the sample diagrams (SVG + WebP)
python blogger/images/optimize_images.py convert DIR    # any raster/SVG -> WebP 1200px into assets/images
python blogger/images/optimize_images.py check          # audit assets/images against the table above
node   blogger/images/compose_caption.mjs in.jpg out.webp --top "…" --bottom "…"
node   blogger/images/compose_caption.mjs --help 2>/dev/null || true
```

Sample files produced for tone review (JHL-4 §3):

| File | Style | What it shows |
| --- | --- | --- |
| `assets/images/llc-filing-fee-breakdown.webp` | Explanatory | Bar chart, 6 states, sample figures clearly labelled as sample |
| `assets/images/first-90-days-timeline.webp` | Explanatory | Four milestones after formation |
| `assets/images/helpful-relative-meme.webp` | Humour | Generated illustration + our caption ("my cousin says…") |
| `assets/images/helpful-relative-diagram.webp` | Humour (variant) | The same joke drawn entirely in SVG |

**Sample figures are illustrative.** Every `.svg` in `samples/` carries a visible
"illustrative sample — replace with cited data" line; the line is removed only when a
guide's numbers have been verified against a primary source.
