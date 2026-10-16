# Test results — JHL-4 Blogger pipeline

Recorded 2026-10-16 (Asia/Seoul) on this machine. Sections 1–4 were recorded before the
owner's OAuth client JSON existed; **section 5 is the live API run added afterwards**,
once the chief of staff confirmed the token in `C:\Users\colds\jhl-secrets\`; **section 6
verifies the applied live theme**. Sections 1–4 stay offline and credential-free, so they
keep working on any machine.

| # | Check | Command | Result |
| --- | --- | --- | --- |
| 1 | Theme XML validator | `python blogger/theme/verify_theme.py` | **all 39 checks passed** |
| 2 | Pipeline test suite | `python blogger/tests/test_pipeline.py` | **43 tests, OK** (0.5 s) |
| 3 | Live-head comparison | `python blogger/theme/compare_live.py` | **matches the theme's assumptions** |
| 4 | Image rules audit | `python blogger/images/optimize_images.py check` | **4/4 files pass** |
| 5 | Draft dry-run, no credentials | `python blogger/publish.py create content/posts/example-guide.md --dry-run --assets-base …` | payload built, exit 0 |
| 6 | Update dry-run (patch path) | `python blogger/publish.py update --slug llc-cost-breakdown content/posts/example-guide.md --dry-run` | gate correctly refused (unresolved `{{ASSET_BASE}}`) |
| 7 | Publish blocked without approval | `python blogger/publish.py publish 123456` | exit 3, "Refusing to publish" |
| 8 | Page create blocked without `--draft` | `python blogger/pages.py create content/pages/about.md` | exit 1, instructs `--draft` |
| 9 | Page dry-run + gate | `python blogger/pages.py create content/pages/privacy-policy.md --dry-run` | payload built, editorial TODO stripped |
| 10 | Secret-value scan | included in suite (`test_no_real_secret_values_in_repo_files`) | no Google access-token, refresh-token or client-secret value appears anywhere under `blogger/` (the scan matches Google's credential prefixes) |
| 11 | **Live write path (post-OAuth)** | `python blogger/tests/smoke_live.py --run` | **SMOKE TEST OK** — draft created, read back, patched, publish refused, deleted, blog left with 0 drafts |
| 12 | **Applied theme + SEO on the live blog** | `python blogger/theme/verify_applied.py` | **exit 0** — theme v1 markers present, og:image / twitter card / viewport / JSON-LD present, canonical & `<title>` exactly once |

## 1. Theme validator — what it actually proved (39 checks)

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

## 2. Pipeline suite — 37 tests (31 offline + 6 regressions)

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

## 5. Live smoke test — 2026-10-16, after the owner's OAuth approval

`python blogger/tests/smoke_live.py --run` — opt-in flag, because this is the only
script under `blogger/` that talks to the network. It creates **one** throwaway draft
on `ownerhandbook.blogspot.com`, exercises the write path, then deletes it and asserts
the blog's draft count is back where it started.

| Step | API call | Observed |
| --- | --- | --- |
| 1 | quality gate + payload (`md2blogger`) | passed: 644 chars, 1 image, labels `['Tools & Software']` |
| 2 | `posts.insert?isDraft=true` | `id=4960114937992198602 status=DRAFT` |
| 3 | `posts.get?view=ADMIN` | read back: `DRAFT`, correct title |
| 4 | `posts.patch` | title updated, same `id`, same `url` (URL preserved) |
| 5 | `posts.publish` with no approval flag | **refused, exit 3** — public transition still gated |
| 6 | ledger write (`content/published.json`) | `smoke-test-pipeline → 4960114937992198602` |
| 7 | `posts.delete` | deleted; ledger entry removed |
| — | `posts.list?status=DRAFT` after | 0 drafts (0 before, 0 after — nothing left behind) |

Final line: `2026-10-16 21:31:05+0900  SMOKE TEST OK`. A second, manual run through the
CLI (`check` → `create` → `get` → `update` → `publish`-refusal → `delete`) produced the
same result.

### What the live run caught (three real bugs, all fixed and covered by new tests)

1. **`posts.get` returns HTTP 404 for a draft** unless `view=ADMIN` (or `AUTHOR`) is
   sent — the default READER view hides drafts even though the same id is returned by
   `posts.list?status=DRAFT`. This broke the whole publish path, because `publish.py`
   reads a post's current status before flipping it. `BloggerClient.get_post` now sends
   `view=ADMIN` by default (`ApiContractTests.test_get_post_asks_for_the_admin_view`).
2. **`posts/search` never matches a draft.** `resolve_post` falls back to search when
   the ledger has no entry, so an unpublished post could look "missing". Documented on
   `search_post`; the ledger (written by `create`) is the primary lookup, as designed.
3. **`os.path.relpath` crashed** when a master lived on a different drive than the repo
   (`ValueError: path is on mount 'C:', start on mount 'E:'`), which would have hit any
   temp/absolute master path. `build_post_payload` now falls back to the absolute path
   (`PathAndHostTests.test_master_outside_the_repo_is_accepted`).

Also fixed while in there: a connection-level failure (offline, DNS, proxy) now raises
`ApiError` with status 0 instead of leaving a raw `URLError` traceback, and the internal-
link check in the quality gate derives the site host from `config.json` instead of
matching a hard-coded `ownerhandbook` prefix (so the blogspot → custom-domain switch
keeps working — the issue forbids hard-coding the URL or site name).

One behaviour worth knowing: for a draft, Blogger returns the **blog** URL as `url`
(there is no permalink until the post is published). Only LIVE posts therefore reach
`content/link-map.json`, which is what the internal-link pass needs.

## 6. Applied theme on the live blog — 2026-10-16, after the owner's manual install

The owner's Backup/Restore upload was rejected by Blogger ("테마를 복원할 수 없습니다" —
a known Blogger problem with third-party theme files), so the theme went in through
**Theme → HTML 편집** (the fallback in `theme/UPLOAD-GUIDE.md` §2-대안). That path is not
visible to the offline validator, so this section verifies it from the outside.

`python blogger/theme/verify_applied.py` — **exit 0**:

| Check (from the rendered page, no credentials) | Result |
| --- | --- |
| Theme markers `.site-header` / `.site-nav` / `.site-footer` / `.ad-slot` CSS rule | all found |
| og:image, twitter card, viewport, JSON-LD | all present |
| canonical link / og:url / `<title>` | exactly 1 each (no duplication of Blogger's own tags) |
| Ad containers `#ad-top`, `#ad-bottom` | present (empty by design) |
| Blogger theme source leaking into the page (`<b:widget`, `<data:`, `expr:`) | none — the theme compiled correctly |

### Two constraints violations this run found and fixed

The delivered theme v1 broke the issue's own "URL·사이트명 하드코딩 금지 (설정값으로)"
rule in two places, and the 37-check validator did not notice — so the validator was
extended first, then the file fixed:

1. **Hard-coded absolute URL.** The og:image fallback for posts without a thumbnail was
   the literal string `https://ownerhandbook.blogspot.com/favicon.ico`. After a
   custom-domain switch that tag would have kept advertising the blogspot host. Now
   derived from `data:blog.homepageUrl`.
2. **Site name baked into body text.** The footer sentence began with the blog name and
   the sidebar widget heading repeated it, so a rename would leave stale text on every
   page. Both are generic now ("About this site", "Independent publication…"); the blog
   name survives only in widget-title settings, which is where Blogger stores it.

New checks `[5b]` (2 of the 39) fail on the previous version of the file and pass on this
one — verified by running the new validator against `git show fa185d5:…xml`:
`2 of 39 checks FAILED` on the old file, `all 39 checks passed` on the fixed file. The same
regression is in the suite (`test_theme_validator_rejects_a_hard_coded_host`).

### The verifier itself had a bug worth recording

The first run reported `3 <title> tags` on a perfectly healthy page. Blogger renders the
theme's source comments into the page and our theme header comment says "<title> tags free
of double quotes", so a naive tag count matches inside comments. Tag counts now strip HTML
comments — but the marker check deliberately does **not**, because Blogger inlines
`<b:skin>` as `<style><!-- … --></style>` and the CSS marker would otherwise disappear.
Both cases are covered by tests.

## Not yet verified (waiting on the owner)

1. ~~Blogger theme upload~~ — **done and verified** (section 6). Note the live copy is the
   version from before the two fixes above; re-applying the same way removes the
   hard-coded fallback URL. Nothing else differs.
2. **Publishing anything public** — deliberately out of scope until the owner reviews
   a draft; the tool refuses without `--confirm-owner-approved`, and the live smoke test
   verified that refusal on the real API.
3. **Real post with real images** — the first end-to-end draft with a genuine guide
   waits for image hosting (`assets.publicBaseUrl`), because the gate refuses a post
   whose image URLs are unresolved. The smoke test used a placeholder base on a draft
   that was deleted in the same run, so no broken image ever reached a reader.
