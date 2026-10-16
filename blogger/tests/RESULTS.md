# Test results — JHL-4 Blogger pipeline

Recorded 2026-10-16 (Asia/Seoul) on this machine, before the owner's OAuth client JSON
existed (`C:\Users\colds\jhl-secrets\` had not been created yet). Everything below runs
offline; the only unverified piece is the live API conversation, which waits for the
owner's one-time approval.

| # | Check | Command | Result |
| --- | --- | --- | --- |
| 1 | Theme XML validator | `python blogger/theme/verify_theme.py` | **all 37 checks passed** |
| 2 | Pipeline test suite | `python blogger/tests/test_pipeline.py` | **31 tests, OK** (0.34 s) |
| 3 | Live-head comparison | `python blogger/theme/compare_live.py` | **matches the theme's assumptions** |
| 4 | Image rules audit | `python blogger/images/optimize_images.py check` | **4/4 files pass** |
| 5 | Draft dry-run, no credentials | `python blogger/publish.py create content/posts/example-guide.md --dry-run --assets-base …` | payload built, exit 0 |
| 6 | Update dry-run (patch path) | `python blogger/publish.py update --slug llc-cost-breakdown content/posts/example-guide.md --dry-run` | gate correctly refused (unresolved `{{ASSET_BASE}}`) |
| 7 | Publish blocked without approval | `python blogger/publish.py publish 123456` | exit 3, "Refusing to publish" |
| 8 | Page create blocked without `--draft` | `python blogger/pages.py create content/pages/about.md` | exit 1, instructs `--draft` |
| 9 | Page dry-run + gate | `python blogger/pages.py create content/pages/privacy-policy.md --dry-run` | payload built, editorial TODO stripped |
| 10 | Secret-value scan | included in suite (`test_no_real_secret_values_in_repo_files`) | no Google access-token, refresh-token or client-secret value appears anywhere under `blogger/` (the scan matches Google's credential prefixes) |

## 1. Theme validator — what it actually proved (37 checks)

- XML well formed; the three Blogger namespaces declared; root `<html>`.
- One `<b:skin>` with 6.0 KB of CSS inside CDATA, inside the lightweight budget.
- 8 widgets, exactly one `Blog`, all widget ids unique, every widget inside a
  `<b:section>`, every widget defines `includable id='main'`.
- **Every `<b:include name='…'/>` resolves inside its own widget** (a dangling include
  is the usual cause of an upload rejection).
- 31 distinct `data:` tags, all inside the classic Layouts v2 whitelist (no v3-only
  tags that Blogger would reject).
- All tag attributes single quoted; prose inside CDATA/comments ignored.
- Feature checks: figure/figcaption styling, three AdSense containers with insertion
  comments, lazy-image handling, `prefers-color-scheme` dark mode, no external
  JavaScript, no web fonts, canonical not duplicated, `data:blog.postImageThumbnailUrl`
  for OG images, `BlogPosting` + `WebSite`/`Organization` JSON-LD.

## 2. Pipeline suite — 31 tests

Conversion: frontmatter parsing, heading shift (`#` → h2), figure + caption + lazy
attributes, missing-caption warning, tables, wrapped list continuation, nested lists,
inline-code escaping, fenced code with language class, editorial-comment stripping,
link-map states (published / declared-but-unpublished / unknown), external link `rel`,
asset-base placeholder.

Quality gate: clean pass, missing image, missing alt, missing figcaption, description
over 150 chars, label outside the Phase 0 model, `<script>` outside the whitelist,
missing description/labels, unresolved placeholders.

Repo/safety: the shipped example guide passes with 2 figures; payload keys are exactly
`title`/`content`/`labels` (nothing undocumented sent to the API); publish refuses
without owner approval; create --dry-run needs no credentials; pages refuse without
`--draft`; no credential values in any committed file.

## 3. Live comparison (ownerhandbook.blogspot.com, fetched for this test)

Blogger itself emits: canonical, generator, Atom/RSS feed links, favicon, `og:url`,
`og:title`, `og:description`, exactly one `<title>`. It does **not** emit: `og:image`,
twitter card, structured data, or a `<meta name="description">` while the blog
description is empty. That is exactly the split the theme assumes — the theme adds
only the missing four, and adds a description fallback (post snippet) that switches
itself off as soon as a real search description exists.

## 4. Images

| File | Size | Dimensions | Verdict |
| --- | --- | --- | --- |
| `assets/images/llc-filing-fee-breakdown.webp` | 24.0 KB | 1200×720 | ok |
| `assets/images/first-90-days-timeline.webp` | 31.5 KB | 1200×620 | ok |
| `assets/images/helpful-relative-meme.webp` | 55.1 KB | 1200×670 | ok |
| `assets/images/helpful-relative-diagram.webp` | 31.2 KB | 1200×620 | ok |

Rendered files were inspected visually: text crisp, nothing clipped, captions legible
(the timeline's first label was clipped in the first render and the layout was fixed
before delivery).

## Not yet verified (waiting on the owner)

1. **Blogger theme upload** — Blogger's own validator only runs inside blogger.com.
   The offline validator covers everything checkable locally; if the upload is
   rejected, the message plus the 1-step rollback in `theme/UPLOAD-GUIDE.md` protects
   the live blog.
2. **Live API draft** — needs `blogger-oauth-client.json` + one approval:
   `python blogger/oauth_login.py`, then `python blogger/publish.py create …` for a
   single draft, coordinated with the owner and the chief of staff.
3. **Publishing anything public** — deliberately out of scope until the owner reviews
   a draft; the tool refuses without `--confirm-owner-approved`.
