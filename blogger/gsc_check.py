#!/usr/bin/env python3
"""Search Console index + sitemap check — read-only monitoring for published posts.

Reads the publishing ledger (content/published.json) and asks the Search Console
URL Inspection API for every LIVE post's index coverage state, then prints the
property's sitemap status. Read-only by design: the OAuth scope is
`webmasters.readonly`, and Google discovers posts through the Blogger sitemap —
so this tool reports state, it never submits a sitemap or requests indexing.

Usage:
    python blogger/gsc_check.py              # every LIVE post in the ledger
    python blogger/gsc_check.py <url> [...]  # specific URLs

Exit codes: 0 = the API answered (whatever the index state is), 2 = the API or
the credentials failed. Newly published posts normally read as "URL is unknown
to Google" until the first crawl; re-run this before the AdSense application to
see what is actually indexed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import blogger_api as api  # noqa: E402

LEDGER = os.path.join(REPO, "content", "published.json")
INSPECT_URL = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"


def live_posts(ledger_path: str = LEDGER) -> list[tuple[str, str]]:
    """(slug, url) for every LIVE post in the ledger, sorted by slug."""
    if not os.path.isfile(ledger_path):
        return []
    with open(ledger_path, encoding="utf-8") as fh:
        ledger = json.load(fh)
    out = []
    for slug, entry in sorted(ledger.items()):
        if entry.get("status") == "LIVE" and entry.get("url"):
            out.append((slug, entry["url"]))
    return out


def inspect(client: api.BloggerClient, prop: str, url: str) -> dict:
    body = {"inspectionUrl": url, "siteUrl": prop}
    resp = client.request("POST", INSPECT_URL, body=body)
    return resp.get("inspectionResult", {}).get("indexStatusResult", {})


def main() -> int:
    parser = argparse.ArgumentParser(description="Search Console index + sitemap check (read-only)")
    parser.add_argument("urls", nargs="*", help="URLs to inspect (default: every LIVE post in the ledger)")
    args = parser.parse_args()

    cfg = api.load_config()
    prop = cfg["blog"]["blogspotUrl"].rstrip("/") + "/"

    try:
        client = api.BloggerClient(cfg)
        sites = [s.get("siteUrl") for s in client.gsc_sites()]
        print(f"Search Console property: {prop}")
        if prop not in sites:
            print(f"  WARN  property not in the authorised site list: {sites}")
        print(f"Token: {api.token_summary(client.token)}")

        targets: list[tuple[str, str]] = []
        if args.urls:
            targets = [("(arg)", u) for u in args.urls]
        else:
            targets = live_posts()
        print(f"\nPosts to inspect: {len(targets)} (from {'arguments' if args.urls else 'content/published.json'})")
        for slug, url in targets:
            state = inspect(client, prop, url)
            print(f"  [{state.get('coverageState', '?')}] {slug}")
            print(f"      verdict={state.get('verdict', '?')} crawled={state.get('lastCrawlTime', '-')}")
            print(f"      {url}")

        print("\nSitemaps for the property:")
        quoted = urllib.parse.quote(prop, safe="")
        sitemaps = client.request("GET", f"{api.GSC_API}/sites/{quoted}/sitemaps").get("sitemap", [])
        if not sitemaps:
            print("  (none listed)")
        for sm in sitemaps:
            print(f"  {sm.get('path')}")
            print(f"      lastDownloaded={sm.get('lastDownloaded', '-')}"
                  f" errors={sm.get('errors', 0)} warnings={sm.get('warnings', 0)}")
    except api.ApiError as exc:
        print(f"API error (credentials or network): {exc}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
