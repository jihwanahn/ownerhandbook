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

- **Now:** the files in `assets/images/` are served by GitHub Pages from this repo
  (`jihwanahn/ownerhandbook`, branch `master`) — connected 2026-10-19. `md2blogger.py`
  reads `assets.publicBaseUrl` from `blogger/config.json` and appends `/` + basename,
  so that value includes the `assets/images` path segment.
- Publishing an image therefore means: regenerate the file here, copy it into
  `assets/images/`, commit, push, and confirm the Pages URL returns 200 **before**
  updating the post. A draft built against an unpublished image URL is worse than no
  draft — the body would ship a broken `<img>`.
- `md2blogger.py` still refuses to emit payloads containing the `{{ASSET_BASE}}`
  placeholder, which is the guard for the case where `publicBaseUrl` is unset.

## 6. Commands

```bash
python blogger/images/build_samples.py                 # redraw the sample diagrams (SVG + WebP)
python blogger/images/optimize_images.py convert DIR    # any raster/SVG -> WebP 1200px into assets/images
python blogger/images/optimize_images.py check          # audit assets/images against the table above
node   blogger/images/compose_caption.mjs in.jpg out.webp --top "…" --bottom "…"
node   blogger/images/compose_caption.mjs --help 2>/dev/null || true
```

Diagrams shipped so far:

| File | Style | What it shows |
| --- | --- | --- |
| `assets/images/llc-filing-fee-breakdown.webp` | Explanatory | Bar chart, 6 states, primary-source filing fees (see §7) |
| `assets/images/first-90-days-timeline.webp` | Explanatory | Four milestones after formation |
| `assets/images/helpful-relative-meme.webp` | Humour | Generated illustration + our caption ("my cousin says…") |
| `assets/images/helpful-relative-diagram.webp` | Humour (variant) | The same joke drawn entirely in SVG |
| `assets/images/ein-paperwork-order.webp` | Explanatory | Timeline: where the EIN sits in the paperwork order (EIN guide) |
| `assets/images/ein-wait-times.webp` | Explanatory | Bar chart, EIN turnaround by application route, IRS-published values (EIN guide) |
| `assets/images/ein-middleman.webp` | Humour | Two panels: a site that charges for an EIN next to irs.gov, both `$0` claims sourced (EIN guide) |
| `assets/images/business-license-three-layers.webp` | Explanatory | Stacked bands: the federal / state / city-county licence layers and who issues each (business-licence guide) |
| `assets/images/business-license-checklist.webp` | Explanatory | Four questions that decide which licence layers apply (business-licence guide) |
| `assets/images/business-license-inspection.webp` | Humour | Two panels: the licence you postpone in month one vs. the overdue-registration letter later (business-licence guide) |

## 7. A number in an image is a citation

An explanatory figure is a claim, and readers cannot click through it to check. So:

- Every figure that shows a number names its source in the image itself, in the same
  file the reader sees (not only in the article body).
- The figures live in `build_samples.py` next to the source for each value, so a
  number and its provenance are edited together. Change one without the other and the
  review should reject it.
- If a number cannot be traced to the agency that charges it, it does not go in the
  figure — rewrite the figure around what can be sourced.
- `build_samples.py` no longer emits a "sample figures" disclaimer: the disclaimers
  were a build-time scaffold for figures awaiting verification, and the shipped figures
  are now verified (2026-10-19). A figure that needs a disclaimer is not ready to
  publish.
