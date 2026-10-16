#!/usr/bin/env python3
"""Compare the live blog's <head> with what the theme relies on (JHL-4 §1 검증).

The issue asks for a structural comparison against the blog that is live today. This
script fetches the public blogspot page and reports which head elements exist, so the
theme's assumptions ("Blogger already emits canonical / description / OG, so the theme
must not duplicate them") stay verifiable instead of remembered.

Usage:
    python blogger/theme/compare_live.py                 # homepage
    python blogger/theme/compare_live.py --url https://ownerhandbook.blogspot.com/2026/10/x.html
Exit code 0 when Blogger's own head output is consistent with the theme's design.
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

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

EXPECT_FROM_BLOGGER = [
    (r"<link[^>]+rel=['\"]canonical['\"][^>]*>", "canonical link (theme must not emit a second one)"),
    (r"<meta[^>]+name=['\"]generator['\"][^>]+content=['\"]blogger['\"][^>]*>|"
     r"<meta[^>]+content=['\"]blogger['\"][^>]+name=['\"]generator['\"][^>]*>", "generator meta"),
    (r"<link[^>]+rel=['\"]alternate['\"][^>]+type=['\"]application/atom\+xml['\"][^>]*>", "Atom/feed links"),
    (r"<link[^>]+rel=['\"]icon['\"][^>]*>", "favicon link"),
    (r"<meta[^>]+property=['\"]og:url['\"][^>]*>", "og:url"),
    (r"<meta[^>]+property=['\"]og:title['\"][^>]*>", "og:title"),
    (r"<meta[^>]+property=['\"]og:description['\"][^>]*>", "og:description"),
]

THEME_ONLY = [
    (r"<meta[^>]+property=['\"]og:image['\"][^>]*>", "og:image (theme adds this)"),
    (r"<meta[^>]+name=['\"]twitter:card['\"][^>]*>", "twitter card (theme adds this)"),
    (r"application/ld\+json", "structured data (theme adds this)"),
]


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", "replace")


def report(html_text: str, url: str) -> int:
    head = html_text[: html_text.find("</head>") + 7] if "</head>" in html_text else html_text
    print(f"URL: {url}\nhead size: {len(head)} chars\n")

    failures = []
    print("Emitted by Blogger itself (the theme relies on these):")
    for pattern, label in EXPECT_FROM_BLOGGER:
        found = re.search(pattern, head, re.I)
        print(f"  {'FOUND   ' if found else 'MISSING '} {label}")
        if not found:
            failures.append(label)

    description = re.search(r"<meta[^>]+name=['\"]description['\"][^>]*content=['\"]([^'\"]*)['\"]", head, re.I)
    print(f"\n  meta description: "
          f"{'present, %d chars' % len(description.group(1)) if description else 'absent (Blogger omits it when empty)'}")
    print("  -> the theme adds a description fallback from the post snippet only when "
          "Blogger's own description is empty, so there is no duplicate tag.")

    print("\nNot emitted by Blogger (the theme must supply these):")
    for pattern, label in THEME_ONLY:
        found = re.search(pattern, head, re.I)
        print(f"  {'present ' if found else 'absent  '} {label}")

    title = re.search(r"<title>(.*?)</title>", head, re.S)
    print(f"\n  <title>: {title.group(1).strip() if title else 'absent'}")
    print(f"  <title> count: {len(re.findall(r'<title', head, re.I))} (must be exactly 1)")

    if len(re.findall(r'rel=["\']canonical["\']', head, re.I)) != 1:
        failures.append("exactly one canonical link")

    print()
    if failures:
        print("RESULT: Blogger's head output differs from the theme's assumptions:")
        for f in failures:
            print(f"  - missing: {f}")
        return 1
    print("RESULT: Blogger's head output matches the theme's assumptions")
    return 0


def main() -> int:
    cfg = api.load_config()
    parser = argparse.ArgumentParser(description="Compare the live blog head with the theme's assumptions")
    parser.add_argument("--url", default=cfg["blog"]["blogspotUrl"] + "/")
    args = parser.parse_args()
    try:
        html_text = fetch(args.url)
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(f"Could not fetch {args.url}: {exc}")
        return 2
    return report(html_text, args.url)


if __name__ == "__main__":
    sys.exit(main())
