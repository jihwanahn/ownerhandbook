# The Owner's Handbook — ownerhandbook.blogspot.com

Content and publishing repo for **The Owner's Handbook**, a small business startup and
operations guide site for a US audience.

- **Live site:** `https://ownerhandbook.blogspot.com` (Blogger, free blogspot address)
- **Local path:** `E:\ownerhandbook`
- **Publishing track (current):** Blogger — see `blogger/README.md`
- **Migration asset (parked):** the Astro static site below. Deployment is on hold
  until a custom domain is connected; the scaffold, its SEO rules and its verify
  scripts are kept working so a migration can resume without rebuild.

## Two things live in this repo

| Directory | Role | Status |
| --- | --- | --- |
| `blogger/`, `content/`, `assets/` | markdown masters, Blogger pipeline, theme, images | **active** — this is how guides get published |
| `src/`, `public/`, `docs/`, `scripts/` | Astro site skeleton (former plan) | parked, build still passes |

Markdown masters are the permanent source of truth: every published guide keeps its
original `.md` in `content/posts/`, so the site can be re-platformed at any time.

## Blogger pipeline (quick reference)

```bash
python blogger/oauth_login.py                     # one-time owner approval (see blogger/README.md)
python blogger/md2blogger.py content/posts/x.md   # convert + quality gate, no network
python blogger/publish.py create content/posts/x.md --assets-base https://<asset-host>
python blogger/publish.py publish <postId> --confirm-owner-approved "who, when"
python blogger/tests/test_pipeline.py             # 31 offline tests
npm run verify:all                                # astro SEO checks + theme + pipeline + images
```

Publishing is **draft-first**: a guide becomes a private Blogger draft, the owner
reviews the preview, and only then is it published.

## Astro site (parked migration asset)

Static site for the same content, built with Astro and prepared for Cloudflare Pages.
- **Stack:** Astro 5 (static output) + `@astrojs/sitemap` + `@astrojs/rss`
- **Hosting:** Cloudflare Pages (free tier), Git-connected to the GitHub repo
- **Site URL (canonical):** `https://ownerhandbook.com` — defined once as `SITE.url`
  in `src/data/site.ts`; every canonical, sitemap entry and schema URL derives from it

## Commands

```bash
npm install          # install dependencies
npm run dev          # local dev server (shows drafts too)
npm run build        # production build -> dist/
npm run preview      # serve dist/ locally
npm run verify       # post-build SEO checks (run after every build)
npm run rename -- --name "…" --domain example.com   # rename/re-domain in one command
node scripts/generate-og-image.mjs   # regenerate public/og-default.png
```

## Content

Guides are markdown files in `src/content/articles/`. The frontmatter contract and
a working example are in `src/content/articles/example-guide.md`.

**Publishing gate:** `draft` defaults to **true**, and production builds exclude
drafts. A new guide cannot reach the live site — or be indexed — until someone
deliberately sets `draft: false`. This is the pre-publication review gate, enforced
by the build rather than by convention.

## Where things live

```
src/
  data/site.ts            site identity, category model, navigation (single source of truth)
  content.config.ts       article schema + publishing gate
  content/articles/       the guides
  layouts/BaseLayout.astro
  components/             Seo, Header, Footer, Breadcrumbs
  pages/
    index.astro                     home
    articles/index.astro            all published guides
    articles/[slug].astro           article template (+ Article JSON-LD)
    categories/index.astro          category directory
    categories/[category].astro     category hub pages
    about | contact | privacy-policy | editorial-policy | 404
    rss.xml.ts                      RSS feed
    robots.txt.ts                   robots.txt, generated from SITE.url
  styles/global.css       all styling (no framework, small payload)
public/
  _headers  favicon.svg  og-default.png
docs/
  DEPLOY.md               deployment runbook (Cloudflare Pages + Vercel)
  SEO.md                  information architecture, metadata and schema rules
```

## Deployment

See `docs/DEPLOY.md`. The site is deploy-ready: connecting the GitHub repo to
Cloudflare Pages (build command `npm run build`, output directory `dist`) is all
that is required to publish.
