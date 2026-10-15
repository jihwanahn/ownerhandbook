# SEO structure — The Owner's Handbook

The rules below are enforced by the code wherever possible, so a new guide cannot
silently break the site's SEO structure.

## 1. Information architecture

Three levels, two clicks maximum from the homepage to any guide:

```
/                                   Home — identity + category grid + latest guides
/categories/                        Category directory
/categories/<slug>/                 Category hub (one per search question)
/articles/                          All published guides, grouped by category
/articles/<slug>/                   Guide
/about/ /contact/ /privacy-policy/ /editorial-policy/    Trust + policy pages
/404/  /rss.xml  /sitemap-index.xml
```

Six fixed category hubs (defined in `src/data/site.ts`, which is the single source
of truth — navigation, hubs, sitemap and JSON-LD all read from it):

| slug | Category | Question it answers |
|---|---|---|
| `start-a-business` | Starting a Business | How do I start this specific business, step by step? |
| `startup-costs` | Startup Costs | What will this business cost me to start and run? |
| `licensing-and-registration` | Licensing & Registration | What licenses, permits and registrations do I legally need? |
| `pricing` | Pricing Your Services | How should I price what I sell so the business is profitable? |
| `tools-and-software` | Tools & Software | Which tools should I buy, and what do they cost at my size? |
| `getting-customers` | Getting Customers | How do I get my first customers and keep the schedule full? |

A guide's `category` frontmatter value is validated against that list at build
time: a typo fails the build instead of creating an orphan page.

## 2. URL and canonical rules

- Trailing slashes everywhere (`trailingSlash: 'always'`); builds emit
  `/about/index.html`. One URL per page, no duplicates.
- `https://ownerhandbook.com` is the only canonical host. `www` redirects to it.
- Every page emits exactly one `<link rel="canonical">` from `Seo.astro`, derived
  from the same `site` value that generates the sitemap — canonicals and sitemap
  cannot drift apart.
- Slugs are keyword-led and stable (e.g. `how-much-does-an-llc-cost-by-state`).
  Changing a published slug requires a redirect entry; do not do it casually.

## 3. Metadata

Per page, via `Seo.astro`:

- `<title>` — `Page title | The Owner's Handbook`; homepage uses the brand alone.
- `<meta name="description">` — 50–200 characters in the schema, written as a
  promise of what the page answers. **Article descriptions are validated by the
  content schema**, so a too-short or too-long description fails the build.
- Open Graph + Twitter `summary_large_image`, image `1200×630`
  (`/og-default.png` by default, article `heroImage` when set).
- `robots` — `index, follow, max-image-preview:large`. `noindex` only for `/404/`.
- `hreflang`: not used — the site is single-language (`en-US`).

## 4. Structured data (JSON-LD)

| Page | Schema |
|---|---|
| Every page | `Organization` + `WebSite` (stable `@id`s: `#organization`, `#website`) |
| Home | `WebPage` + `ItemList` of categories |
| Categories directory | `CollectionPage` + `ItemList` |
| Category hub | `CollectionPage` + `ItemList` of its guides |
| Guide | `Article` (`headline`, `image`, `datePublished`, `dateModified`, `author`, `publisher`, `articleSection`, `citation` from sources) |
| Guide + category | `BreadcrumbList` (visible trail and markup share one source) |
| About / Contact / Policy pages | `AboutPage` / `ContactPage` / `WebPage` |

All blocks reference the shared `#organization` / `#website` ids rather than
redefining the publisher, which is what Google's entity resolution prefers.

## 5. Internal linking

- Home → category hubs; category hub → its guides, its planned cluster and the
  sibling categories; footer → every category + all policy pages (so every page is
  reachable from every page).
- Guides link to related guides: `related:` frontmatter slugs first, then
  same-category articles fill the block automatically.
- Breadcrumbs on every hub and guide, mirroring the URL path.
- AdSense review favours a crawlable, non-orphaned structure: no guide ships
  without at least one inbound link from its category hub.

## 6. Technical

- `robots.txt` allows all crawlers, explicitly allows `Mediapartners-Google` and
  `AdsBot-Google` (AdSense), disallows only `/404/`, and declares the sitemap.
- `sitemap-index.xml` / `sitemap-0.xml` generated at build from the same routes;
  `/404` and thank-you pages are filtered out.
- `_headers` (Cloudflare) sets security headers and a 1-year immutable cache for
  hashed `/_astro/*` assets.
- Performance: no framework, one small CSS file, no third-party JS by default,
  system font stack (no webfont request), `<img>` with explicit dimensions.
  The OG image is generated locally by `scripts/generate-og-image.mjs`.

## 7. Publishing gate

`src/content.config.ts` sets `draft: true` as the default. Production builds
exclude any article whose `draft` is not explicitly `false`, so:

- `npm run dev` shows drafts for internal review;
- `npm run build` (and therefore anything deployed) contains only approved guides;
- an unapproved draft is not merely noindexed — it is not in the output at all.

Phase 2 publishing flow: draft → review → set `draft: false` → build → deploy →
submit the URL in Search Console.

## 8. New-guide checklist (Phase 2)

- [ ] One specific search question; keyword-led slug
- [ ] `description` 50–200 chars; `category` set (build validates both)
- [ ] At least 2 primary sources with real agency/vendor URLs in `sources`
- [ ] Numbers in tables with stated assumptions
- [ ] Every factual claim traceable to a linked source
- [ ] `related` slugs point at guides that actually exist
- [ ] General-information disclaimer present (rendered automatically on each guide)
- [ ] Representative review recorded; only then `draft: false`
