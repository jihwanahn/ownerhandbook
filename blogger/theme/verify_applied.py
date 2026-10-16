#!/usr/bin/env python3
"""Check whether theme v1 is actually live, and that its SEO tags survived the install.

The owner applies the theme by hand (Theme -> Edit HTML, or Backup/Restore -> Upload), so
"did it land?" and "did the SEO tags make it into the rendered page?" are two questions
that were previously answered by eyeballing the blog. This script answers both from the
live HTML, using markers that only exist in our theme, so the acceptance check in JHL-4
can be run by anyone at any time.

Blogger renders <b:skin> CSS and the theme's own markup into every page, so the checks
work on the homepage even before the first post is published.

Usage:
    python blogger/theme/verify_applied.py                       # homepage from config.json
    python blogger/theme/verify_applied.py --url <post url>      # a guide page (item)
Exit codes:
    0  theme v1 is live and its SEO tags are correct
    1  theme v1 is live but something is wrong with the SEO output
    3  theme v1 is not applied yet (the live page still looks like a stock Blogger theme)
    2  the page could not be fetched
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import blogger_api as api  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

# Markers that exist only in our theme: class names it introduces plus a CSS token from
# its <b:skin>. A stock Blogger theme has none of them, so absence is a clean signal.
THEME_MARKERS = [
    (r"class='site-header'|class=\"site-header\"", "header wrapper (.site-header)"),
    (r"class='site-nav'|class=\"site-nav\"", "category/page nav (.site-nav)"),
    (r"class='site-footer'|class=\"site-footer\"", "footer wrapper (.site-footer)"),
    (r"\.ad-slot", "theme CSS is inlined (.ad-slot rule)"),
]

# Tags the theme adds because Blogger does not emit them (see compare_live.py).
THEME_SEO = [
    (r"<meta[^>]+property=['\"]og:image['\"]", "og:image"),
    (r"<meta[^>]+name=['\"]twitter:card['\"]", "twitter card"),
    (r"<meta[^>]+name=['\"]viewport['\"]", "viewport meta (mobile-first)"),
    (r"application/ld\+json", "JSON-LD structured data"),
]

# Tags Blogger emits itself; the theme must not duplicate them.
BLOGGER_SEO = [
    (r"<link[^>]+rel=['\"]canonical['\"]", "canonical link"),
    (r"<meta[^>]+property=['\"]og:url['\"]", "og:url"),
]

AD_SLOTS_INDEX = ("ad-top", "ad-bottom")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", "replace")


def report(html_text: str, url: str) -> int:
    head = html_text[: html_text.find("</head>") + 7] if "</head>" in html_text else html_text
    # Blogger renders the theme's source comments into the page, and our theme's header
    # comment mentions <title> and canonical. Counting tags without stripping comments
    # reports "3 <title> tags" on a perfectly healthy page, so strip them first.
    head_tags = re.sub(r"<!--.*?-->", "", head, flags=re.S)
    body_tags = re.sub(r"<!--.*?-->", "", html_text, flags=re.S)

    print(f"URL: {url}\npage size: {len(html_text)} chars\n")

    print("[1] Theme v1 markers")
    missing_markers = []
    for pattern, label in THEME_MARKERS:
        # Raw markup on purpose: Blogger inlines <b:skin> inside `<style><!-- ... --></style>`,
        # so the CSS-rule marker below only matches before comments are stripped.
        found = re.search(pattern, html_text, re.I)
        print(f"  {'FOUND   ' if found else 'MISSING '} {label}")
        if not found:
            missing_markers.append(label)

    if len(missing_markers) == len(THEME_MARKERS):
        print("\nRESULT: theme v1 is NOT applied yet — the live page has none of the theme's")
        print("        markers, so it is still on the stock Blogger theme.")
        print("        Nothing to fix here: apply it from blogger/theme/UPLOAD-GUIDE.md,")
        print("        then re-run this script to confirm.")
        return 3
    if missing_markers:
        print(f"\n  ({len(missing_markers)} marker(s) missing — the theme may be applied but")
        print("   edited. Continuing with the SEO checks.)")

    print("\n[2] SEO tags the theme is responsible for")
    seo_failures = []
    for pattern, label in THEME_SEO:
        found = re.search(pattern, head_tags, re.I)
        print(f"  {'PASS ' if found else 'FAIL '} {label}")
        if not found:
            seo_failures.append(label)

    print("\n[3] Tags Blogger emits (the theme must not duplicate them)")
    duplicates = []
    for pattern, label in BLOGGER_SEO:
        count = len(re.findall(pattern, head_tags, re.I))
        print(f"  {'PASS ' if count == 1 else 'FAIL '} {label}: {count} occurrence(s), expected 1")
        if count != 1:
            duplicates.append(f"{label} x{count}")

    titles = len(re.findall(r"<title[\s>]", head_tags, re.I))
    print(f"  {'PASS ' if titles == 1 else 'FAIL '} <title>: {titles}, expected 1")
    if titles != 1:
        duplicates.append(f"<title> x{titles}")

    description = re.search(r"<meta[^>]+name=['\"]description['\"][^>]*content=['\"]([^'\"]*)['\"]",
                            head_tags, re.I)
    print(f"\n  meta description: {len(description.group(1))} chars" if description
          else "\n  meta description: absent (Blogger omits it until a search description"
               " exists; the theme falls back to the post snippet on guide pages)")

    print("\n[4] Ad slots")
    for slot in AD_SLOTS_INDEX:
        found = re.search(rf"id=['\"]{slot}['\"]", body_tags)
        print(f"  {'FOUND   ' if found else 'ABSENT  '} #{slot}"
              + ("" if found else " (expected only when the page lists at least one post)"))

    problems = seo_failures + duplicates
    print()
    if problems:
        print("RESULT: theme v1 is live, but these checks failed:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("RESULT: theme v1 is live and its SEO tags are correct")
    return 0


def main() -> int:
    cfg = api.load_config()
    parser = argparse.ArgumentParser(
        description="Verify that theme v1 is applied to the live blog and its SEO tags are correct")
    parser.add_argument("--url", default=cfg["blog"]["blogspotUrl"] + "/")
    args = parser.parse_args()
    try:
        html_text = fetch(args.url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"Could not fetch {args.url}: {exc}")
        return 2
    return report(html_text, args.url)


if __name__ == "__main__":
    sys.exit(main())
