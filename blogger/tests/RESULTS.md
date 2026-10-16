# Test results — JHL-4 Blogger pipeline

Recorded 2026-10-16 (Asia/Seoul) on this machine. Sections 1–4 were recorded before the
owner's OAuth client JSON existed; **section 5 is the live API run added afterwards**,
once the chief of staff confirmed the token in `C:\Users\colds\jhl-secrets\`. Sections
1–4 stay offline and credential-free, so they keep working on any machine.

| # | Check | Command | Result |
| --- | --- | --- | --- |
| 1 | Theme XML validator | `python blogger/theme/verify_theme.py` | **all 37 checks passed** |
| 2 | Pipeline test suite | `python blogger/tests/test_pipeline.py` | **37 tests, OK** (0.9 s) |
| 3 | Live-head comparison | `python blogger/theme/compare_live.py` | **matches the theme's assumptions** |
| 4 | Image rules audit | `python blogger/images/optimize_images.py check` | **4/4 files pass** |
| 5 | Draft dry-run, no credentials | `python blogger/publish.py create content/posts/example-guide.md --dry-run --assets-base …` | payload built, exit 0 |
| 6 | Update dry-run (patch path) | `python blogger/publish.py update --slug llc-cost-breakdown content/posts/example-guide.md --dry-run` | gate correctly refused (unresolved `{{ASSET_BASE}}`) |
| 7 | Publish blocked without approval | `python blogger/publish.py publish 123456` | exit 3, "Refusing to publish" |
| 8 | Page create blocked without `--draft` | `python blogger/pages.py create content/pages/about.md` | exit 1, instructs `--draft` |
| 9 | Page dry-run + gate | `python blogger/pages.py create content/pages/privacy-policy.md --dry-run` | payload built, editorial TODO stripped |
| 10 | Secret-value scan | included in suite (`test_no_real_secret_values_in_repo_files`) | no Google access-token, refresh-token or client-secret value appears anywhere under `blogger/` (the scan matches Google's credential prefixes) |
| 11 | **Live write path (post-OAuth)** | `python blogger/tests/smoke_live.py --run` | **SMOKE TEST OK** — draft created, read back, patched, publish refused, deleted, blog left with 0 drafts |

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

## Not yet verified (waiting on the owner)

1. **Blogger theme upload** — Blogger's own validator only runs inside blogger.com.
   The offline validator covers everything checkable locally; if the upload is
   rejected, the message plus the 1-step rollback in `theme/UPLOAD-GUIDE.md` protects
   the live blog. This is the only item left on the owner's side.
2. **Publishing anything public** — deliberately out of scope until the owner reviews
   a draft; the tool refuses without `--confirm-owner-approved`, and the live smoke test
   verified that refusal on the real API.
3. **Real post with real images** — the first end-to-end draft with a genuine guide
   waits for image hosting (`assets.publicBaseUrl`), because the gate refuses a post
   whose image URLs are unresolved. The smoke test used a placeholder base on a draft
   that was deleted in the same run, so no broken image ever reached a reader.
