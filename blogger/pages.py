#!/usr/bin/env python3
"""About / Contact / Privacy policy pages (JHL-4 §2 — pages.insert).

Pages are what AdSense reviewers and readers look for (the JHL-3 checklist requires a
privacy policy that names cookies and Google advertising). Blogger's pages API has no
isDraft flag on insert, so `create --draft` inserts the page and immediately reverts it
to draft state; publishing is a second, explicitly approved step.

Usage:
    python blogger/pages.py list
    python blogger/pages.py create content/pages/about.md --dry-run
    python blogger/pages.py create content/pages/about.md --draft
    python blogger/pages.py publish <pageId> --confirm-owner-approved "who, when"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import blogger_api as api  # noqa: E402
import md2blogger  # noqa: E402


def build_page_payload(md_path: str, cfg: dict) -> dict:
    with open(md_path, encoding="utf-8") as fh:
        raw = fh.read()
    meta, body_md = md2blogger.parse_frontmatter(raw)
    warnings: list[str] = []
    html_body = md2blogger.convert(body_md, cfg, {}, warnings, None)
    audit = md2blogger.TagAudit()
    audit.feed(html_body)
    unknown = sorted(audit.tags - md2blogger.ALLOWED_TAGS)
    if unknown:
        raise SystemExit(f"page body uses tags outside the Blogger whitelist: {unknown}")
    title = meta.get("title")
    if not title:
        raise SystemExit("page frontmatter needs a title")
    return {"title": title, "content": html_body, "labels": meta.get("labels", []), "warnings": warnings}


def cmd_list(cfg, args) -> int:
    client = api.BloggerClient(cfg)
    pages = client.list_pages()
    print(f"{len(pages)} page(s):")
    for page in pages:
        print(f"  [{page.get('status', '?')}] {page.get('id')}  {page.get('title')}  {page.get('url')}")
    return 0


def cmd_create(cfg, args) -> int:
    page = build_page_payload(args.markdown, cfg)
    for warn in page.pop("warnings", []):
        print(f"  WARN  {warn}")
    print(f"Page payload: title={page['title']!r} body={len(page['content'])} chars")
    if args.dry_run:
        print("DRY RUN — no request sent. Payload:")
        print(json.dumps(page, ensure_ascii=False, indent=2)[:4000])
        return 0
    if not args.draft:
        raise SystemExit("Refusing: pass --draft (insert + revert to draft) so the owner can review first, "
                         "or publish later with pages.py publish.")
    client = api.BloggerClient(cfg)
    created = client.insert_page(page)
    page_id = created["id"]
    print(f"Page inserted: id={page_id} url={created.get('url')}")
    reverted = client.request("POST", f"{api.BLOGGER_API}/blogs/{client.blog_id}/pages/{page_id}/revert")
    print(f"Reverted to draft: status={reverted.get('status')}")
    print(f"Review in Blogger -> Pages, then: python blogger/pages.py publish {page_id} "
          f"--confirm-owner-approved \"<who, when>\"")
    return 0


def cmd_update(cfg, args) -> int:
    page = build_page_payload(args.markdown, cfg)
    page.pop("warnings", None)
    if args.dry_run:
        print("DRY RUN — would PATCH:")
        print(json.dumps(page, ensure_ascii=False, indent=2)[:2000])
        return 0
    client = api.BloggerClient(cfg)
    updated = client.patch_page(args.page_id, page)
    print(f"Page updated: id={updated.get('id')} status={updated.get('status')} url={updated.get('url')}")
    return 0


def cmd_publish(cfg, args) -> int:
    if not args.confirm_owner_approved:
        print("Refusing to publish: needs the owner's review first.")
        print("Re-run with --confirm-owner-approved \"<who, when>\".")
        return 3
    client = api.BloggerClient(cfg)
    page = client.request("POST", f"{api.BLOGGER_API}/blogs/{client.blog_id}/pages/{args.page_id}/publish")
    approvals = os.path.join(HERE, "approvals.json")
    log = json.load(open(approvals, encoding="utf-8")) if os.path.isfile(approvals) else []
    log.append({"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "approvedBy": args.confirm_owner_approved,
                "action": "publish-page", "target": args.page_id})
    with open(approvals, "w", encoding="utf-8") as fh:
        json.dump(log, fh, ensure_ascii=False, indent=2)
    print(f"Page published: {page.get('url')}")
    return 0


def main() -> int:
    cfg = api.load_config()
    parser = argparse.ArgumentParser(description="Blogger static pages (About/Contact/Privacy)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")

    p_create = sub.add_parser("create")
    p_create.add_argument("markdown")
    p_create.add_argument("--dry-run", action="store_true")
    p_create.add_argument("--draft", action="store_true", help="insert then revert to draft (required)")

    p_update = sub.add_parser("update")
    p_update.add_argument("page_id")
    p_update.add_argument("markdown")
    p_update.add_argument("--dry-run", action="store_true")

    p_pub = sub.add_parser("publish")
    p_pub.add_argument("page_id")
    p_pub.add_argument("--confirm-owner-approved", dest="confirm_owner_approved", metavar="WHO_WHEN")

    args = parser.parse_args()
    return {"list": cmd_list, "create": cmd_create, "update": cmd_update, "publish": cmd_publish}[args.command](cfg, args)


if __name__ == "__main__":
    sys.exit(main())
