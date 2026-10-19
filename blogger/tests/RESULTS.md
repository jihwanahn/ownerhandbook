# Test results — JHL-4 Blogger pipeline

Recorded 2026-10-16 (Asia/Seoul) on this machine. Sections 1–4 were recorded before the
owner's OAuth client JSON existed; **section 5 is the live API run added afterwards**,
once the chief of staff confirmed the token in `C:\Users\colds\jhl-secrets\`; **section 6
verifies the applied live theme**. Sections 1–4 stay offline and credential-free, so they
keep working on any machine.

| # | Check | Command | Result |
| --- | --- | --- | --- |
| 1 | Theme XML validator (v1) | `python blogger/theme/verify_theme.py blogger/theme/owners-handbook-v1.xml` | **all 45 checks passed** |
| 1b | Theme XML validator (declaration variant) | `python blogger/theme/verify_theme.py blogger/theme/owners-handbook-v2-decl.xml` | **all 49 checks passed** |
| 2 | Pipeline test suite | `python blogger/tests/test_pipeline.py` | **61 tests, OK** (0.8 s) |
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

## 7. The live theme does not render a single widget — found 2026-10-16

The re-check of the live blog found a failure that section 6's checks could not see: the
theme is applied and its SEO tags are correct, but **every section renders empty**, so the
page shows nothing but "Skip to content".

`python blogger/theme/verify_applied.py` — **exit 4** (new code, `[5]` below):

| Observed on the live page | Value |
| --- | --- |
| Sections | all 5 rendered as `<div class='… no-items section' id='…'></div>` |
| Widget wrapper elements (`<div class='widget …' id='…'>`) | **0** |
| Widgets Blogger registered client-side (`_RegisterWidget`) | 6 (Header1, PageList1, Blog1, HTML1, PageList2, HTML2) |
| Widgets the theme declares | **8** — Label1 and Label2 are not instantiated at all |
| The "text" a reader sees | `Skip to content` |
| Same blog on `?m=1` (stock mobile template, different template slot) | 9 widgets render normally |

Reading: Blogger knows the widget **model** (it registered the widgets and computed their
settings — the `Pages` widget even carried the `Home` link and the blog title), but emitted
**no widget markup**. That is the shape of a theme whose widgets were never instantiated in
the blog's layout, not of a broken theme file — the file compiles (no `<b:widget`/`<data:`
leak in the page, CSS inlined, markers present).

Also found while measuring:

- **The theme never declared its layout generation.** `<html>` carried no `b:version='2'`,
  no `class='v2'` and no `b:responsive='true'`; every theme Blogger renders widgets for has
  them, including the stock template serving this blog's `?m=1`. Added to the file, with
  new validator checks `[2b]` (3 of the 42) and a parsed-root regression test.
- **The live copy is the post-fix version** — the page still carries the fix-bundle comment
  ("derived from `data:blog.homepageUrl` so no host or site name is hard-coded here"), so the
  owner did re-save after `2e60151` and section 6's §4-1 caveat is stale. Only the new
  `<html>` declarations (section 7) still need one paste.
- **Mobile is served by a different template slot.** `?m=1` renders the stock Blogger
  template (navbar/crosscol/footer-1/3) with Korean Blogger strings (`글이 없습니다`, `홈`),
  because the theme is not declared responsive. `b:responsive='true'` addresses it; the blog's
  own language setting (currently `ko`) is what those strings follow.
- **`verify_applied.py` passed this page before this run.** Markers and SEO tags are not
  evidence that a theme works, so the new `[5]` check reports each declared widget as
  `RENDERED / REGISTERED BUT EMPTY / NOT INSTANTIATED` and returns exit 4 when the sections
  are empty. Regression tests replay the real page shape (`EMPTY_WIDGET_PAGE`).

Diagnosis order and the bisect baseline theme are in `blogger/theme/bisect/PLAN.md`
(`python blogger/theme/verify_theme.py blogger/theme/bisect/B0-baseline.xml` is *not* part
of `npm run verify:all` — it is a throwaway diagnostic, not a design).

## 8. Confirmation of §7 — 2026-10-17, and one hypothesis killed

Confirmation needed nothing from the owner: the live page was re-read after the chief of
staff reported a re-save. `python blogger/theme/verify_applied.py` → **exit 4**, with the two
new checks passing:

| Question | Answer |
| --- | --- |
| Is the *current* file the one being served? | **Yes** — the served `<html>` element carries `class='v2'` (new check `[1b]`) |
| Is the mobile slot on the theme? | **Yes** — `?m=1` renders our marker set, no `navbar`/`crosscol` sections, no Korean Blogger strings (new check `[6]`) |
| Do the widgets render? | **No** — still 0 wrapper elements, 5 empty `no-items` sections, 6 registered but empty |

**Killed: §7's explanation of the widget failure.** The `<html>` declarations are in effect
and all five sections are still empty, so the missing declarations were *not* what stopped
Blogger from instantiating widgets. Two independent pieces of evidence:

- The failure reproduces identically with and without the declarations (exit 4 before the
  re-save and after it).
- A working control: the owner's other blog (`keineideehabeich.blogspot.com`, stock theme)
  renders 20 widget wrappers in a page whose served element is just
  `<html dir='ltr' lang='en'>` — **no `class='v2'` at all**. That token is not what makes
  widgets render. What the declarations did fix is real and stays: `?m=1` moved off the stock
  template onto this theme, and `[6]` now guards it (mobile readers were seeing a different
  section set and Korean UI strings).

Independent report of the identical symptom (support.google.com/blogger/thread/463778303,
2026-08-30): sections render as empty `no-items` divs while the page's own JS data blob
carries the real post data, with no console errors — and the reporter had already ruled out
widget `version='1'` vs `'2'`, widget/section id collisions and one dangling `b:include`.
Their key record: **a minimal 2-widget version of the same theme renders correctly on the
same blog while the full version silently fails.** That is the bisect route already planned
in `blogger/theme/bisect/PLAN.md`, and it means hand-pasted themes can render widgets in
general — which §7's "the layout was never instantiated" reading alone cannot explain.
`PLAN.md` now carries the corrected order: Layout save → B0 baseline → bisect, with the
re-paste step demoted to "only if `[1b]` says the served page is stale".

Also recorded: the blog's own locale is `ko` (Blogger settings → language, owner-side), which
is where the Korean UI strings in `?m=1` came from while the stock template served it.

## 9. Declaration-generation variant, and the checks that keep it honest — 2026-10-17

Chief of staff asked for the "modernise the widget declarations" fix as the first-path
experiment (`ownerhandbook-v2-decl`), with v1 kept untouched as the rollback. Delivered,
plus the offline checks that make the experiment falsifiable.

### The evidence behind the hypothesis (reproduced here, not taken on report)

```
curl -s https://ownerhandbook.blogspot.com/ | grep -c _RegisterWidget      -> 7
curl -s https://ownerhandbook.blogspot.com/ | grep -c "no-items section"   -> 5
curl -s https://ownerhandbook.blogspot.com/ | grep -ci "id='Label1'|id='Label2'" -> 0
grep -c "class='widget"                                                    -> 0
```

The 7 registrations are `Header1`(header), `BlogSearch1`(nav), `PageList1`(nav),
`Blog1`(main-posts), `HTML1`(sidebar), `PageList2`(footer), `HTML2`(footer) — and the
served `<html>` element carries `class='v2'` but no `b:version`/`b:responsive` (those are
compile-time). So the layout holds **6 instances for 5 declared sections plus one extra
(`BlogSearch1`)**, while the theme declares **8 widgets**: `Label1` and `Label2` have no
instance, `BlogSearch1` has no declaration. Blogger renders neither the extras nor the
declared-but-uninstantiated ones, and it renders nothing at all for the sections it does
have instances for.

### What shipped

| File | What it is |
| --- | --- |
| `blogger/theme/owners-handbook-v2-decl.xml` | v1 **with declarations only** changed: `<html b:defaultwidgetversion='2'>`, all 8 widgets `version='2' visible='true'`, all 5 sections `name='Header/Navigation/Posts/Sidebar/Footer'`. `b:layoutsVersion='3'` deliberately **not** added (v3-only token; these data tags are v2-model). |
| `blogger/theme/decl_variant.py` | The generator. Text-level attribute edits (no re-serialisation), so CSS, includables, data tags, ad slots and widget settings cannot drift. `--check` fails if the committed variant is stale. |

The full `diff` between v1 and the variant is 8 hunks: one `<html>` line, five section
lines, and each widget's own line. A test asserts the two files are byte-identical after
**stripping the declaration attributes**, so "declarations only" is enforced, not asserted
in prose.

### New validator checks `[2c]` and the honest limit of them

`verify_theme.py` gained a `[2c]` block: one uniform widget version token, no
`b:layoutsVersion='3'`, `visible=` a real boolean wherever it appears — plus, **when the
file declares `b:defaultwidgetversion='2'`**, that the widgets match it, every widget
carries an explicit `visible=`, and every section carries a unique Layout name. v1
**45 checks**, variant **49 checks**, both exit 0. Offline checks cannot prove Blogger
will render the widgets; what they can do is make sure the variant is exactly the
declared experiment and nothing more.

### Suite

`python blogger/tests/test_pipeline.py` → **61 tests, OK** (53 + 8): the derivation
proof, the variant's validator run, v1 not regressing under the new checks, three
negative cases (mixed widget generations, a v3 layout token, a generation-2 section
without a name), the guide-drift guard, and the `--check` mode.

### Observations recorded, not yet acted on

- `BlogSearch1` is a residual layout instance the theme does not declare, sitting in the
  `nav` section (`maxwidgets='2'`, layout holds PageList1 + BlogSearch1 + the
  uninstantiated Label1). If widgets start rendering, that box needs deleting in
  Layout; the upload guide now says so.
- `Label1`/`Label2` still have no instance. If they never appear, the fallback is adding
  the label widgets directly under Layout.

## Not yet verified (waiting on the owner)

1. ~~Blogger theme upload~~ — **applied and verified** (section 6), the served copy is the
   current file (section 8, check `[1b]`), and the mobile slot is on the theme (check `[6]`).
   What is still open is the widget rendering itself (sections 7–10). The owner's next steps,
   in order: **one Layout save / built-in theme round-trip → apply
   `owners-handbook-v3-decl.xml` (upload, or the manual paste) → `bisect/B0-probe.xml` if it
   is still empty**; `verify_applied.py` judges each step (exit 0 = done), and
   `verify_applied.py --bisect` judges the probe step.
2. **Publishing anything public** — deliberately out of scope until the owner reviews
   a draft; the tool refuses without `--confirm-owner-approved`, and the live smoke test
   verified that refusal on the real API.
3. **Real post with real images** — the first end-to-end draft with a genuine guide
   waits for image hosting (`assets.publicBaseUrl`), because the gate refuses a post
   whose image URLs are unresolved. The smoke test used a placeholder base on a draft
   that was deleted in the same run, so no broken image ever reached a reader.

---

## 10. Layouts v3 declaration surface + the bisect probe (2026-10-18)

Directed by the chief of staff (comment `5951a544`): the live page is our theme, the layouts
are known to Blogger, and **no widget markup is produced at all**. Two deliverables were
asked for — fold `B0-probe.xml` into the verifier/tests, and prepare a two-file v3 variant —
plus one change to the validator's `b:layoutsVersion='3'` rule.

### Files

| File | What it is | Checks |
| --- | --- | --- |
| `blogger/theme/owners-handbook-v3-decl.xml` | v2-decl + `b:layoutsVersion='3'` + `<head><b:defaultmarkups>` (17 widget types, intentionally empty). Nothing else moves. | 57 |
| `blogger/theme/owners-handbook-v3-tags.xml` | the above + the data-tag model mapped to v3 (second variable, isolated) | 59 |
| `blogger/theme/v3_variant.py` | derives both from `owners-handbook-v2-decl.xml`; `--check` (exit 1 when stale) | — |
| `blogger/theme/bisect/B0-probe.xml` | the diagnostic theme + two fresh-id probes, reviewed and amended | — |

**Grounding.** Every mapped token was checked against real, working v3 themes
(`vtrick 1.9.0`, `tech-jet-core-12-21`, `jobzeek`) — no guessed tag. Where no grounded v3
counterpart exists, the tag is replaced by literal text (`LITERAL_REPLACEMENTS`: e.g.
`Filed under:`), never by an invented token. v2-only tokens (`blog.pageType`,
`blog.pageName`, `blog.postImageThumbnailUrl`, `post.timestampISO8601`, `post.numComments`)
are forbidden in the tags variant and the validator enforces it.

### Proof, not prose

- `python blogger/theme/v3_variant.py --check` → exit 0:
  `OK: v3-decl == v2-decl + layoutsVersion/defaultmarkups, v3-tags == v3-decl + grounded data-tag mapping`
- Tests are written on the *stripped* texts (declarations removed / data tags replaced), so
  "only the declarations moved" is enforced by the test suite, not by a claim.
- `[2c]`/`[2d]` now judge the declaration surface per generation: a v1/v2 file must **not**
  carry `b:layoutsVersion='3'`; a v3 file must carry it **with** `<b:defaultmarkups>` inside
  `<head>`, one empty block per widget type the file actually uses. The pair is the
  exception, never the token alone — the raw token is still rejected (regression test kept).

### Bugs found by running the tools

1. **`<b:defaultmarkups>` inside a comment ate half the file.** The theme's own header comment
   mentions the tag while explaining it, so a loose `<b:defaultmarkups>.*?</b:defaultmarkups>`
   pattern started matching inside the comment and deleted ~15 kB (body, widgets, footer) —
   the "declarations only" proof silently compared the wrong text. Both the stripper and the
   test now anchor the block to the start of a line, and the ordering (block first, then the
   comment) is required because removing the comment first re-indents the tag out of anchor
   range.
2. **`--bisect` markers must be markup, not settings.** For a widget id the layout already
   holds, Blogger can render the widget with the layout's *stored* text, so a missing setting
   proves nothing. The probe now also carries a markup marker inside `HTML1`
   (`B0-EXISTING-ID-WIDGET-RENDERED`), and a test pins it inside the includable.
3. **A `--bisect` inserted into an XML comment** — `--` is illegal in XML comments. XML
   well-formedness now runs over both bisect files in the test suite (this caught it).

### Verification

- `npm run verify:all` → **exit 0** (Astro SEO + theme v1 **48** + v2-decl **52** +
  v3-decl **57** + v3-tags **59** + pipeline **84** tests + images 4/4)
- `verify_applied.py` → **exit 4** live (theme applied, mobile slot on our theme, widgets
  still 0 — unchanged pre-experiment state, as expected)
- `verify_applied.py --bisect` → verdicts exercised offline against fixtures for all four
  branches (fresh probes / existing-id only / theme-served-only / older theme still served)
- No publication of any kind, no secret outside its local file, no spending, no AdSense or
  hiring touched.

## 11. Figures verified against primary sources + the draft rebuilt (2026-10-19)

The owner connected GitHub Pages (JHL-1) and the chief of staff created the first draft
(`postId 4880096691114614728`). Before it could be published, every number in it had to
be traced to the agency that charges it. This section records what changed and how it was
checked; it supersedes §4 (whose figures were placeholders) and the "sample figures"
disclaimer those figures carried.

### The number check

| Claim as written | Verified value | Source |
| --- | --- | --- |
| filing fee $50 – $500 | **$35 – $500** | Montana $35 (sosmt.gov), Kentucky $40 (sos.ky.gov), Massachusetts $500 (sec.state.ma.us) |
| registered agent $0 – $150/yr | **$0 – $250/yr** | $0 self-appointed; Northwest $125, ZenBusiness $199, LegalZoom $249 |
| annual report $0 – $800/yr | **$0 – $800/yr**, row renamed "annual report or state renewal" | $0 (AZ/MO/NM); MA $500 report; the $800 is California's annual minimum franchise tax (ftb.ca.gov), not a report fee |
| bank account $0 – $180/yr | **$0 – $360/yr** | $0 online-only; $15/mo (Wells Fargo Initiate) to $29.95/mo (BofA Business Advantage) unless the balance waiver is met |
| chart: New York $205 | **$200** | dos.ny.gov fee schedule; the $205 quoted elsewhere adds a $5 plain-copy fee |
| formation service "+$100 – $300" | **"$0 to about $300"** | free tiers exist (Bizee, Inc Authority, LegalZoom Basic, ZenBusiness) alongside $39 (Northwest) and $249 (LegalZoom Pro) |

Also verified and left unchanged: Texas $300 (sos.state.tx.us), Florida $125 (dos.fl.gov —
$100 filing + $25 registered agent), Wyoming $100 (sos.wyo.gov), California $70 (sos.ca.gov).

### What the article and the images gained

- The guide carries a **"Where these numbers come from"** section naming the source class
  for each row, and the chart carries its own source line *inside the image* — a reader
  cannot click through a chart, so the citation travels with it (`IMAGE-RULES.md` §7).
- `build_samples.py` no longer emits the "illustrative sample" scaffold; the figures now
  sit in the source next to their provenance so a number and its citation are edited
  together.

### Internal links — the policy decision

The gate reported three internal-link warnings on the first draft. The policy applied:

1. **The self-reference is removed.** `[[llc-cost-breakdown|this guide]]` pointed at the
   article the reader was already on. That is a defect, not a missing link.
2. **Forward references stay as pending text.** `[[start-a-business|where to start]]`
   resolves to a `<span class="link-pending">` — visible words, no dead link — and becomes
   a real `<a>` automatically once that guide is published and `content/link-map.json`
   gains its URL. Keeping it in the master preserves the authoring intent.
3. **The "2+ internal links" target is deferred, not waived.** The blog has zero published
   posts and zero published pages (sitemap is empty), so no internal link target exists
   yet. The gate treats the count as a **warning** and `link-missing` as an **error**, which
   is the right split: post #1 ships with the warning, and the target starts binding from
   the second published guide.

### Verification

- `npm run verify:all` → **exit 0** (Astro SEO + theme 48/52/57/59 + pipeline **84** tests
  + images 4/4)
- Chart and timeline fetched back from `jihwanahn.github.io` and **md5-compared to the local
  files** — the draft's image URLs serve the verified bytes, not a cached older copy
- Draft read back from the Blogger API and asserted field by field (14 checks: DRAFT status,
  every corrected range, the renamed row, the sources section, both image URLs, no
  self-link, no placeholder, no sample disclaimer, 2 figures with 2 captions) — **all PASS**
- No publication: the post is still a draft. No secret left its local file. No AdSense,
  hiring or spending touched.

### Defect found in the test suite (fixed here)

`test_asset_base_missing_leaves_placeholder` and `test_placeholder_blocks_the_gate_without_asset_base`
asserted the "no asset base configured" path while reading the **live** `blogger/config.json`.
The moment JHL-1 set `assets.publicBaseUrl`, they began failing — the suite was red at
`fac90e3` and the earlier "84 tests pass" claim did not hold at that commit. Both tests now
supply their own config (`CFG_WITHOUT_ASSETS`), so they test what they claim to rather than
whether the image host happens to be connected.

