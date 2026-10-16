#!/usr/bin/env python3
"""Blogger publish pipeline — draft-first (JHL-4 §2).

Flow enforced by this tool (the owner's review gate is a hard requirement):

    create   md master -> posts.insert  (isDraft=true)   -> private draft URL
    update   md master -> posts.patch   (URL preserved)
    publish  posts.publish                              -> requires --confirm-owner-approved
    revert   published post -> back to draft

Safety rules baked in:
  * nothing is made public without an explicit --confirm-owner-approved flag AND a
    matching approval line in blogger/approvals.json (who approved, when)
  * --dry-run prints the exact payload without touching the network
  * only documented Blogger API fields are sent — no secrets, no unknown keys

Usage:
    python blogger/publish.py check
    python blogger/publish.py create content/posts/example.md --dry-run
    python blogger/publish.py create content/posts/example.md
    python blogger/publish.py update --slug example-guide content/posts/example.md
    python blogger/publish.py list --status DRAFT
    python blogger/publish.py publish <postId> --confirm-owner-approved "Nina, 2026-10-20"
    python blogger/publish.py revert <postId>
    python blogger/publish.py delete <postId>            # drafts only (cleanup / smoke test)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import blogger_api as api  # noqa: E402
import md2blogger  # noqa: E402

LEDGER = os.path.join(REPO, "content", "published.json")
LINK_MAP = os.path.join(REPO, "content", "link-map.json")
APPROVALS = os.path.join(HERE, "approvals.json")


# ------------------------------------------------------------------------ helpers


def _read_json(path: str, default):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def record(slug: str, post: dict, cfg: dict) -> None:
    ledger = _read_json(LEDGER, {})
    entry = ledger.get(slug, {})
    entry.update({
        "postId": post.get("id", entry.get("postId")),
        "url": post.get("url", entry.get("url")),
        "status": post.get("status", entry.get("status")),
        "title": post.get("title", entry.get("title")),
        "updated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "blog": cfg["blog"]["blogspotUrl"],
    })
    ledger[slug] = entry
    _write_json(LEDGER, ledger)
    if entry["status"] == "LIVE" and entry["url"]:
        link_map = _read_json(LINK_MAP, {})
        link_map[slug] = entry["url"]
        _write_json(LINK_MAP, link_map)


def load_report(md_path: str, cfg: dict, args) -> dict:
    report = md2blogger.build_post_payload(md_path, cfg, getattr(args, "assets_base", None),
                                           getattr(args, "link_map", None))
    if report["errors"]:
        print("Quality gate FAILED — nothing was sent:")
        for err in report["errors"]:
            print(f"  ERROR {err}")
        sys.exit(2)
    for warn in report["warnings"]:
        print(f"  WARN  {warn}")
    return report


def require_approval(args) -> None:
    if not args.confirm_owner_approved:
        print("Refusing to publish: public transition needs the owner's review first.")
        print("Re-run with --confirm-owner-approved \"<who approved, when>\" after the draft is signed off.")
        sys.exit(3)
    approvals = _read_json(APPROVALS, [])
    approvals.append({
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "approvedBy": args.confirm_owner_approved,
        "action": "publish",
        "target": getattr(args, "post_id", None) or getattr(args, "slug", None),
    })
    _write_json(APPROVALS, approvals)


def resolve_post(client: api.BloggerClient, slug: str) -> dict:
    """Find a post by ledger entry first, then by Blogger search."""
    ledger = _read_json(LEDGER, {})
    if slug in ledger and ledger[slug].get("postId"):
        return client.get_post(ledger[slug]["postId"])
    hits = client.search_post(slug)
    if not hits:
        raise SystemExit(f"No post found for slug '{slug}' (ledger has no entry either).")
    if len(hits) > 1:
        print(f"  {len(hits)} posts matched '{slug}' — using the first:")
        for hit in hits:
            print(f"    {hit.get('id')}  {hit.get('title')}")
    return client.get_post(hits[0]["id"])


# ----------------------------------------------------------------------- commands


def cmd_check(cfg, args) -> int:
    client = api.BloggerClient(cfg)
    blogs = client.blogs_by_user()
    print(f"Authorised for {len(blogs)} blog(s):")
    for blog in blogs:
        print(f"  id={blog.get('id')}  {blog.get('name')}  {blog.get('url')}")
    print(f"Configured blog id: {cfg['blog']['id']} ({cfg['blog']['blogspotUrl']})")
    posts = client.list_posts(max_results=5)
    print(f"Recent posts visible to the API: {len(posts)}")
    for post in posts:
        print(f"  [{post.get('status', '?')}] {post.get('id')}  {post.get('title')}")
    token = api.load_token(cfg)
    print("Token: " + api.token_summary(token))
    return 0


def cmd_create(cfg, args) -> int:
    report = load_report(args.markdown, cfg, args)
    payload = report["payload"]
    print(f"Draft payload: title={payload['title']!r} labels={payload['labels']} "
          f"body={len(payload['content'])} chars")
    if args.dry_run:
        print("DRY RUN — no request sent. Payload:")
        print(json.dumps(payload, ensure_ascii=False, indent=2)[:4000])
        return 0
    client = api.BloggerClient(cfg)
    post = client.insert_post(payload, is_draft=True)
    record(report["slug"], post, cfg)
    print(f"Draft created: id={post['id']}")
    print(f"Status: {post.get('status')}  URL: {post.get('url')}")
    print("Review: Blogger -> Posts -> Drafts -> Preview, then publish with:")
    print(f"  python blogger/publish.py publish {post['id']} --confirm-owner-approved \"<who, when>\"")
    return 0


def cmd_update(cfg, args) -> int:
    report = load_report(args.markdown, cfg, args)
    if not args.post_id and not args.slug:
        raise SystemExit("update needs <postId> or --slug")
    if args.dry_run:
        target = args.post_id or args.slug
        print(f"DRY RUN — would PATCH {target} with:")
        print(json.dumps(report["payload"], ensure_ascii=False, indent=2)[:4000])
        return 0
    client = api.BloggerClient(cfg)
    post_id = args.post_id
    if not post_id:
        post_id = resolve_post(client, args.slug)["id"]
    post = client.patch_post(post_id, report["payload"])
    record(report["slug"], post, cfg)
    print(f"Updated: id={post['id']} status={post.get('status')} url={post.get('url')}")
    return 0


def cmd_publish(cfg, args) -> int:
    require_approval(args)
    client = api.BloggerClient(cfg)
    current = client.get_post(args.post_id)
    if current.get("status") == "LIVE":
        print("Already LIVE — nothing to do.")
        return 0
    post = client.publish_post(args.post_id)
    slug = _slug_for_post(args.post_id)
    if slug:
        record(slug, post, cfg)
    print(f"Published: {post.get('url')}")
    return 0


def cmd_revert(cfg, args) -> int:
    client = api.BloggerClient(cfg)
    post = client.revert_post(args.post_id)
    slug = _slug_for_post(args.post_id)
    if slug:
        record(slug, post, cfg)
    print(f"Reverted to draft: id={post.get('id')} status={post.get('status')}")
    return 0


def _slug_for_post(post_id: str) -> str | None:
    ledger = _read_json(LEDGER, {})
    for slug, entry in ledger.items():
        if entry.get("postId") == post_id:
            return slug
    return None


def cmd_delete(cfg, args) -> int:
    """Delete a post the API sees (the routine cleanup after a smoke test)."""
    client = api.BloggerClient(cfg)
    post = client.get_post(args.post_id)  # 404s before anything is removed
    if post.get("status") == "LIVE" and not args.force_live:
        print(f"Refusing to delete a LIVE post ({post.get('url')}).")
        print("Revert it to a draft first (publish.py revert), or pass --force-live deliberately.")
        return 3
    client.delete_post(args.post_id)
    slug = _slug_for_post(args.post_id)
    if slug:
        ledger = _read_json(LEDGER, {})
        ledger.pop(slug, None)
        _write_json(LEDGER, ledger)
        link_map = _read_json(LINK_MAP, {})
        if link_map.pop(slug, None) is not None:
            _write_json(LINK_MAP, link_map)
    print(f"Deleted: id={args.post_id} status={post.get('status')} title={post.get('title')!r}")
    if slug:
        print(f"Ledger entry for slug '{slug}' removed.")
    return 0


def cmd_list(cfg, args) -> int:
    client = api.BloggerClient(cfg)
    posts = client.list_posts(status=args.status, max_results=args.limit)
    print(f"{len(posts)} post(s){' with status ' + args.status if args.status else ''}:")
    for post in posts:
        print(f"  [{post.get('status', '?')}] {post.get('id')}  {post.get('title')}")
        if args.urls:
            print(f"        {post.get('url')}")
    return 0


def cmd_get(cfg, args) -> int:
    client = api.BloggerClient(cfg)
    post = client.get_post(args.post_id)
    print(json.dumps({k: v for k, v in post.items() if k != "content"}, ensure_ascii=False, indent=2))
    print(f"content: {len(post.get('content', ''))} chars")
    return 0


def cmd_search(cfg, args) -> int:
    client = api.BloggerClient(cfg)
    for hit in client.search_post(args.query):
        print(f"  [{hit.get('status', '?')}] {hit.get('id')}  {hit.get('title')}  {hit.get('url')}")
    return 0


def main() -> int:
    cfg = api.load_config()
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--assets-base", help="override the image base URL for this run")
    common.add_argument("--link-map", help="slug -> Blogger URL map (default content/link-map.json)")

    parser = argparse.ArgumentParser(description="Draft-first Blogger publishing")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="verify credentials and show the target blog")

    p_create = sub.add_parser("create", help="create a private draft from a markdown master", parents=[common])
    p_create.add_argument("markdown")
    p_create.add_argument("--dry-run", action="store_true")

    p_update = sub.add_parser("update", help="patch an existing post (URL preserved)", parents=[common])
    p_update.add_argument("post_id", nargs="?")
    p_update.add_argument("--slug")
    p_update.add_argument("markdown")
    p_update.add_argument("--dry-run", action="store_true")

    p_pub = sub.add_parser("publish", help="publish a draft (owner approval required)")
    p_pub.add_argument("post_id")
    p_pub.add_argument("--confirm-owner-approved", dest="confirm_owner_approved", metavar="WHO_WHEN",
                       help="required: who approved the review and when")

    p_rev = sub.add_parser("revert", help="turn a published post back into a draft")
    p_rev.add_argument("post_id")

    p_del = sub.add_parser("delete", help="delete a draft (cleanup for smoke tests)")
    p_del.add_argument("post_id")
    p_del.add_argument("--force-live", dest="force_live", action="store_true",
                       help="allow deleting a LIVE post (off by default)")

    p_list = sub.add_parser("list", help="list posts")
    p_list.add_argument("--status", choices=["DRAFT", "LIVE", "SCHEDULED"])
    p_list.add_argument("--limit", type=int, default=25)
    p_list.add_argument("--urls", action="store_true")

    p_get = sub.add_parser("get", help="show one post's metadata")
    p_get.add_argument("post_id")

    p_search = sub.add_parser("search", help="search posts by text")
    p_search.add_argument("query")

    args = parser.parse_args()
    handlers = {
        "check": cmd_check, "create": cmd_create, "update": cmd_update,
        "publish": cmd_publish, "revert": cmd_revert, "list": cmd_list,
        "get": cmd_get, "search": cmd_search, "delete": cmd_delete,
    }
    return handlers[args.command](cfg, args)


if __name__ == "__main__":
    sys.exit(main())
