# blogger/ — Blogger publishing toolchain

Scripts and assets for the Blogger track (JHL-4). The Astro site in the repo root is
kept as a migration asset; this directory is what actually publishes to
`ownerhandbook.blogspot.com`.

```
blogger/
  config.json           blog id, hosts, label model, paths, asset base (no secrets)
  blogger_api.py        Blogger API v3 client + OAuth token handling (stdlib only)
  oauth_login.py        one-time owner approval (loopback OAuth)
  publish.py            draft-first posts: create / update / publish / revert / list
  pages.py              About / Contact / Privacy as Blogger pages (draft-first)
  md2blogger.py         markdown master -> Blogger HTML + quality gate
  theme/                two theme files (v1 + declaration variant) + generator + validator + owner upload guide
  images/               image generation, WebP normalisation, audit (see IMAGE-RULES.md)
  tests/                 offline suite + live smoke test + recorded results
content/                markdown masters (posts/ and pages/) — permanent source of truth
assets/images/          published image files (WebP, 1200px)
```

## Why Python (and why stdlib only)

The issue left the language open, so: **Python 3, standard library only.**

- `python` is already on this machine (3.14.7); nothing to install, nothing to keep
  upgraded, and the same command works for the owner, for me and for any later agent.
- The entire Blogger surface we need is five HTTP calls (auth URL, token exchange,
  token refresh, REST call, Search Console call). `google-api-python-client` +
  `google-auth` would add ~30 packages and a lockfile for no extra capability.
- Markdown conversion is a bounded subset (headings, lists, tables, figures, code,
  quotes, links) with house rules attached — a 60-line converter we control beats a
  general parser we would have to constrain anyway.
- Node is used for one job only: image encoding through `sharp` (libvips), which
  rasterises SVG and writes WebP without a system dependency chain.

## One-time setup (owner — DONE 2026-10-16, see JHL-1 §2 for the GCP steps)

1. GCP → APIs & Services → enable **Blogger API v3** (optionally Search Console API).
2. OAuth consent screen → External → scopes
   `https://www.googleapis.com/auth/blogger` and
   `https://www.googleapis.com/auth/webmasters.readonly` → **Publish** the app
   (a "Testing" app expires refresh tokens after 7 days).
3. Credentials → Create credentials → **OAuth client ID → Desktop app** → download
   the JSON to `C:\Users\colds\jhl-secrets\blogger-oauth-client.json`.
4. Approve once:

```bash
python blogger/oauth_login.py          # opens the browser; click Allow
python blogger/oauth_login.py --check  # confirms the refresh token works and lists blogs
```

The owner completed all four steps on 2026-10-16 (chief of staff logged it on JHL-4);
`--check` reports two authorised blogs and the target blog id. The refresh token lives
in `C:\Users\colds\jhl-secrets\blogger-oauth-token.json`.
**Secrets never leave those two files** — not into comments, issues, commits or logs.
`tests/test_pipeline.py` includes a check that no real credential value appears
anywhere under `blogger/`.

If the token ever stops working, re-run step 4 — nothing else needs to change.

Still to do on the Blogger side (owner, in the Blogger UI): Settings → Basics → the
blog title/description, Settings → Crawlers and indexing → custom robots.txt and
custom robots header tags, and Settings → Comments. Values are prepared by the chief
of staff as part of the Phase 1 checklist.

## Publish flow (draft-first, always)

```bash
# 1. author: content/posts/<slug>.md   (frontmatter: title, slug, description, labels)
# 2. convert + gate, no network:
python blogger/md2blogger.py content/posts/example-guide.md --assets-base https://<asset-host>
# 3. private draft:
python blogger/publish.py create content/posts/example-guide.md --assets-base https://<asset-host>
# 4. owner reviews the draft preview in Blogger
# 5. publish only after sign-off:
python blogger/publish.py publish <postId> --confirm-owner-approved "who, when"
# cleanup a throwaway or abandoned draft (drafts only unless --force-live):
python blogger/publish.py delete <postId>
```

- `create` uses `posts.insert?isDraft=true`; `update` uses `posts.patch` (URL kept);
  `publish`/`revert` use `posts.publish` / `posts.revert`; `delete` uses `posts.delete`
  and drops the ledger entry.
- `--dry-run` works for `create` and `update` with no credentials at all.
- `publish` refuses to run without `--confirm-owner-approved`, and every approval is
  appended to `blogger/approvals.json`.
- Drafts are recorded in `content/published.json` (postId, url, status); a slug's
  live URL is copied into `content/link-map.json` so later guides can link to it.
- **Drafts and the API (learned the hard way, see `tests/RESULTS.md` §5):** `posts.get`
  answers 404 for a draft unless it is asked with `view=ADMIN` (the client does this by
  default now), `posts/search` never returns a draft, and a draft's `url` field is the
  blog's home page because Blogger only mints a permalink on publish.
- **Search descriptions:** Blogger API v3 has no field for them (`Post` has no
  `searchDescription`; only the editor writes it). The theme therefore emits the post
  snippet as a description fallback, and `md2blogger.py` reports the intended text so
  the reviewer can paste it into the editor if a custom one is wanted.

## Quality gate

`md2blogger.py` blocks a draft when: the body is empty; there is no image; a
`<figure>` lacks `<figcaption>`; an `<img>` lacks `alt`; the search description is
missing or over 150 characters; a label is outside the six Phase 0 categories; a tag
falls outside the Blogger whitelist; or an image URL is still `{{ASSET_BASE}}`.
Warnings (not blocking): title over ~65 characters, fewer than two internal links,
non-kebab image filenames, missing `loading="lazy"`.

## Tests

```bash
python blogger/tests/test_pipeline.py                 # 84 offline tests, no network
python blogger/theme/verify_theme.py blogger/theme/owners-handbook-v1.xml \
                                     blogger/theme/owners-handbook-v2-decl.xml \
                                     blogger/theme/owners-handbook-v3-decl.xml \
                                     blogger/theme/owners-handbook-v3-tags.xml   # 48 + 52 + 57 + 59
python blogger/theme/decl_variant.py --check          # declarations only (v1 -> v2-decl)
python blogger/theme/v3_variant.py --check            # v3 surface only, then data tags only
python blogger/theme/verify_applied.py                # theme live? widgets rendering? SEO tags? (reads the public page)
python blogger/theme/verify_applied.py --bisect       # reads the B0-probe markers and prints the verdict
python blogger/images/optimize_images.py check        # image rules
python blogger/tests/smoke_live.py --run              # live write path (writes 1 throwaway draft)
```

Four theme files ship, and each step between them is one variable (see `tests/RESULTS.md`
§9–§10): `owners-handbook-v1.xml` is what the blog serves today; `owners-handbook-v2-decl.xml`
modernises the widget/section **declarations** (`b:defaultwidgetversion='2'`, widgets
`version='2' visible='true'`, named sections); `owners-handbook-v3-decl.xml` adds the
**Layouts v3 declaration surface** (`b:layoutsVersion='3'` + an empty
`<b:defaultmarkups>` block per widget type); `owners-handbook-v3-tags.xml` then maps the
**data-tag model** to v3. v3 tags are only ever taken from real working v3 themes — where no
grounded counterpart exists the tag becomes literal text, never a guess.
`decl_variant.py` and `v3_variant.py` derive each file from the one before it — never edit
them by hand — and tests prove that stripping the declaration attributes (or the mapped data
tags) yields identical text.
`verify_theme.py` validates each file separately (any number of paths may be given).

`test_pipeline.py` never touches the network or the credentials, so it runs anywhere.
`smoke_live.py` is the opposite: it is the only script that talks to Blogger, needs an
explicit `--run`, creates one throwaway draft, deletes it again and fails if the blog's
draft count changed. Run it after any change to `blogger_api.py` or the publish path.

`verify_applied.py` reads the public page (no credentials) and answers the questions the
offline validator cannot: whether the **current** theme file is the one being served, whether
its **widgets render**, whether the **mobile slot** (`?m=1`) is on the theme, and whether its
SEO tags survived the install. Exit `0` = current file live, rendering and correct,
`1` = live with an SEO problem, `4` = live but every section is an empty `no-items` div
(see `blogger/theme/bisect/PLAN.md`), `5` = desktop is fine but Blogger's stock template still
serves `?m=1` (mobile-first), `3` = the current file is not what the blog serves (not applied,
or an older generation — check `[1b]`). It is deliberately **not** part of `npm run verify:all`,
because `3`, `4` and `5` are legitimate states of the live blog (it is applied by hand) and
would fail unrelated builds.

Results of the runs recorded for this issue: `blogger/tests/RESULTS.md`.
