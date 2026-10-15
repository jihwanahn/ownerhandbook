# Deployment runbook — ownerhandbook.com

Everything below is ready to execute the moment the accounts exist. The repository
builds clean (`npm run build` → `dist/`), so no code changes are expected.

## What is needed from the accounts side

| Requirement | Why | Status |
|---|---|---|
| Domain `ownerhandbook.com` registered (Cloudflare Registrar recommended) | canonical URL, Search Console, AdSense ownership | representative is purchasing |
| GitHub repo (public or private — either works; private + Pages Git integration is fine) | source of truth + deploy trigger | **connection needed** |
| Cloudflare account (same one that registers the domain) | hosting + DNS + analytics | **connection needed** |
| Google account | Search Console + Analytics + later AdSense | **connection needed** |

Until GitHub/Cloudflare are connected, everything below is prepared but not executed.

## Option A — Cloudflare Pages with Git integration (recommended)

Automatic deploys on every push to `main`, with preview deploys on branches.

1. Push this repo to GitHub (`ownerhandbook`).
2. Cloudflare dashboard → **Workers & Pages → Create → Pages → Connect to Git** →
   select the repo.
3. Build settings:
   - Framework preset: **Astro**
   - Build command: `npm run build`
   - Build output directory: `dist`
   - Environment variable (optional): `NODE_VERSION = 22`
4. Deploy. The first build produces `https://<project>.pages.dev`.
5. **Custom domain:** Pages project → Custom domains → add `ownerhandbook.com`
   and `www.ownerhandbook.com`.
   - Since the domain is registered at Cloudflare, the DNS records are created
     automatically. `www` should redirect to the apex domain (Pages handles the
     redirect when both are added; set the redirect rule if it prompts).
   - Keep one canonical host: the site's canonical tags and sitemap all use the
     **apex** `https://ownerhandbook.com`, so the `www` host must redirect, not
     serve its own copy.

## Option B — Cloudflare Pages direct upload (no Git, fastest to first deploy)

Use if the GitHub connection is delayed but Cloudflare access exists.

```bash
cd E:/ownerhandbook
npm run build
npx wrangler pages deploy dist --project-name ownerhandbook
```

Then attach the custom domain in the dashboard. Note: direct upload does **not**
deploy on push — re-run the command for each release, so switch to Option A once
GitHub is connected.

## Option C — Vercel (fallback)

`Import Project` → framework Astro is auto-detected → add the domain. Nothing in
the repo is Cloudflare-specific except `public/_headers` (Cloudflare header rules),
which Vercel ignores; on Vercel, security headers would move to `vercel.json`.

## Post-deploy verification checklist

```bash
curl -sI https://ownerhandbook.com/                 # 200, correct canonical host
curl -s  https://ownerhandbook.com/robots.txt       # sitemap line present
curl -s  https://ownerhandbook.com/sitemap-index.xml
curl -sI https://ownerhandbook.com/www-redirect     # www -> apex
```

- [ ] `https://ownerhandbook.com/` loads over HTTPS with a valid certificate
- [ ] `http://` and `www.` both 301/308 to the apex HTTPS URL
- [ ] `/robots.txt` resolves and points at `sitemap-index.xml`
- [ ] `/sitemap-index.xml` lists all pages and no `404`
- [ ] `/rss.xml` resolves
- [ ] A sample page's `<link rel="canonical">` matches the live URL
- [ ] Rich Results Test passes for Article and BreadcrumbList (once articles exist)
- [ ] PageSpeed Insights mobile ≥ 95 for Performance/SEO/Best Practices

## Search Console setup

1. Add property: **Domain** property for `ownerhandbook.com` (DNS verification —
   one TXT record at Cloudflare; this verifies http/https and all subdomains).
2. Submit `https://ownerhandbook.com/sitemap-index.xml` under **Sitemaps**.
3. Use **URL Inspection → Request Indexing** for the homepage and each published
   guide (Phase 2 flow: request indexing as part of publishing).
4. Confirm Indexing → Pages shows "Crawled — currently not indexed" resolving to
   indexed over the following days.
5. Set up the **email alert** for coverage/manual-action issues so a future Google
   action does not go unnoticed.

## Analytics

Cloudflare Web Analytics is cookieless (no consent banner implications, and the
Privacy Policy already covers it). Enable it in the Cloudflare dashboard and paste
the beacon `<script>` into `src/layouts/BaseLayout.astro` where the comment marks
the spot. If GA4 is added instead, the cookie disclosure in the Privacy Policy is
already written for it.

## Analytics/GSC + AdSense ordering

Phase 3 needs: site live → guides indexed → AdSense application. The `ads.txt`
file and the AdSense verification snippet are **not** in this repo yet on purpose —
they require the AdSense publisher ID, which does not exist until the account is
created. When it does: add `public/ads.txt` with the publisher line and insert the
AdSense script in `BaseLayout.astro`.
