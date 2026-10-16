#!/usr/bin/env python3
"""Live smoke test — proves the Blogger write path works end to end (JHL-4 §2).

creates ONE throwaway draft on the configured blog, reads it back, patches it,
checks that publishing is still refused without owner approval, then deletes it and
asserts the blog is back to its earlier draft count.

This is the only script in blogger/ that talks to the network, so it is opt-in:

    python blogger/tests/smoke_live.py --run

It never publishes: the public transition stays behind the owner's review gate. The
throwaway master carries a placeholder asset base because image hosting (GitHub
Pages) is not connected yet; the draft is deleted in the same run, so no broken
image URL ever reaches a reader.

Exit code 0 = the whole cycle succeeded and nothing was left behind.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BLOGGER = os.path.dirname(HERE)
REPO = os.path.dirname(BLOGGER)
sys.path.insert(0, BLOGGER)

import blogger_api as api  # noqa: E402
import publish as pub  # noqa: E402

SMOKE_SLUG = "smoke-test-pipeline"
PLACEHOLDER_BASE = "https://placeholder.invalid/jhl-assets"

MASTER = """---
title: Smoke Test — Pipeline Connectivity (throwaway)
slug: {slug}
description: Throwaway draft used to verify the Blogger API write path end to end. Deleted immediately after the check.
labels: [Tools & Software]
category: tools-and-software
status: draft
---

This draft exists only to prove the publishing pipeline can write to the Blogger API.
The smoke test deletes it in the same run.

![LLC filing fee breakdown](assets/images/llc-filing-fee-breakdown.webp "Sample chart on a placeholder asset base while image hosting is not connected.")

Visit the [blog home](https://{host}/) or browse
[starting a business](https://{host}/search/label/Starting%20a%20Business).
"""


def step(label: str) -> None:
    print(f"\n--- {label}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Live Blogger write-path smoke test")
    ap.add_argument("--run", action="store_true", help="required: this touches the live blog")
    args = ap.parse_args()
    if not args.run:
        print("Refusing to run: pass --run to acknowledge this writes one throwaway draft.")
        return 2

    cfg = api.load_config()
    host = cfg["blog"]["blogspotUrl"].split("//")[-1].strip("/")
    client = api.BloggerClient(cfg)
    before = {p["id"] for p in client.list_posts(status="DRAFT", max_results=50)}
    print(f"Blog: {cfg['blog']['blogspotUrl']}  ({len(before)} draft(s) before)")

    tmpdir = tempfile.mkdtemp(prefix="jhl4-smoke-")
    master = os.path.join(tmpdir, "smoke-test-pipeline.md")
    with open(master, "w", encoding="utf-8") as fh:
        fh.write(MASTER.format(slug=SMOKE_SLUG, host=host))

    post_id = None
    ok = True
    try:
        step("1. quality gate + payload")
        report = pub.load_report(master, cfg, argparse.Namespace(
            assets_base=PLACEHOLDER_BASE, link_map=None))
        print(f"   gate passed: {len(report['payload']['content'])} chars, "
              f"{report['image_count']} image(s), labels={report['payload']['labels']}")

        step("2. posts.insert(isDraft=true)")
        post = client.insert_post(report["payload"], is_draft=True)
        post_id = post["id"]
        print(f"   id={post_id} status={post.get('status')}")

        step("3. posts.get (view=ADMIN — default view 404s on drafts)")
        got = client.get_post(post_id)
        assert got["status"] == "DRAFT", got.get("status")
        print(f"   read back: status={got['status']} title={got['title']!r}")

        step("4. posts.patch (URL preserved)")
        patched = client.patch_post(post_id, {"title": report["payload"]["title"] + " [patched]"})
        assert patched["id"] == post_id, "patch changed the post id"
        assert patched.get("url") == got.get("url"), "patch changed the post URL"
        print(f"   title now {patched['title']!r}  url unchanged: {patched.get('url')}")

        step("5. posts.publish without owner approval must be refused")
        proc = subprocess.run(
            [sys.executable, os.path.join(BLOGGER, "publish.py"), "publish", post_id],
            capture_output=True, text=True)
        assert proc.returncode == 3, f"expected refusal (3), got {proc.returncode}"
        print(f"   refused with exit {proc.returncode}: {proc.stdout.strip().splitlines()[0]}")

        step("6. ledger bookkeeping")
        pub.record(SMOKE_SLUG, post, cfg)
        ledger = pub._read_json(pub.LEDGER, {})
        assert ledger.get(SMOKE_SLUG, {}).get("postId") == post_id, "ledger entry missing"
        print(f"   content/published.json records {SMOKE_SLUG} -> {post_id}")

    except Exception as exc:  # noqa: BLE001 - report, then clean up
        ok = False
        print(f"\nFAILED: {type(exc).__name__}: {exc}")
    finally:
        if post_id:
            step("7. cleanup — posts.delete")
            try:
                current = client.get_post(post_id)
                client.delete_post(post_id)
                print(f"   deleted {post_id} (was {current.get('status')})")
            except api.ApiError as exc:
                if exc.status == 404:
                    print(f"   {post_id} already gone")
                else:
                    ok = False
                    print(f"   cleanup failed: HTTP {exc.status} {exc.body[:160]}")
            ledger = pub._read_json(pub.LEDGER, {})
            if SMOKE_SLUG in ledger:
                ledger.pop(SMOKE_SLUG)
                pub._write_json(pub.LEDGER, ledger)
                print(f"   ledger entry for {SMOKE_SLUG} removed")
        else:
            step("7. cleanup — nothing was created")
        try:
            os.remove(master)
            os.rmdir(tmpdir)
        except OSError:
            pass

    after = {p["id"] for p in client.list_posts(status="DRAFT", max_results=50)}
    left = after - before
    print(f"\nDrafts after: {len(after)} (was {len(before)})")
    if left:
        ok = False
        print(f"LEFTOVERS: {sorted(left)}")

    stamp = time.strftime("%Y-%m-%d %H:%M:%S%z")
    print(f"{stamp}  {'SMOKE TEST OK' if ok else 'SMOKE TEST FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
