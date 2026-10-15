# The Owner's Handbook — ownerhandbook.com

Static site for **The Owner's Handbook**, a small business startup and operations
guide site for a US audience. Built with Astro, deployed to Cloudflare Pages.

- **Local path:** `E:\ownerhandbook`
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
