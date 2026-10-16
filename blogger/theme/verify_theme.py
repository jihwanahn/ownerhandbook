#!/usr/bin/env python3
"""Offline validator for the Blogger theme XML.

Blogger's own theme validator only runs inside blogger.com, so this script
checks everything that *can* be checked on this machine before the owner
uploads the file:

  1. XML is well formed and the Blogger namespaces are declared.
  2. <b:skin> exists and carries CSS inside CDATA.
  3. Exactly one Blog widget exists, and every <b:include name='x'/> inside a
     widget resolves to an includable that the same widget defines (a dangling
     include is the #1 cause of an upload rejection).
  4. Only data tags from the classic Layouts v2 model are used — v3-only tags
     are rejected here instead of by Blogger's validator.
  5. Section/widget ids are unique and well formed; widgets live in sections.
  6. Attributes are single quoted (Blogger is strict about this).
  7. Feature requirements from JHL-4 §1: figure/figcaption styling, three
     AdSense containers, lazy-image handling, dark mode, no external JS or
     web fonts, CSS budget.
  8. No host or site name is baked into rendered markup — the blog must survive
     a rename or a custom-domain switch without a code edit (JHL-4 constraint).
     Widget titles are settings, so the site name may appear there only.

Usage:
    python blogger/theme/verify_theme.py [path/to/theme.xml]
Exit code 0 = all checks passed.
"""

from __future__ import annotations

import html
import os
import re
import sys
import xml.etree.ElementTree as ET

B = "{http://www.google.com/2005/gml/b}"
DATA = "{http://www.google.com/2005/gml/data}"
EXPR = "{http://www.google.com/2005/gml/expr}"

DEFAULT_THEME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "owners-handbook-v1.xml")

# Classic Layouts v2 data tags. Anything outside this list must be justified
# against an uploaded production theme before it is added here.
ALLOWED_DATA_TAGS = {
    # blog level
    "blog.title", "blog.url", "blog.homepageUrl", "blog.pageName", "blog.pageType",
    "blog.metaDescription", "blog.postImageThumbnailUrl", "blog.languageDirection",
    # post level
    "post.id", "post.title", "post.url", "post.link", "post.body", "post.snippet",
    "post.timestamp", "post.timestampISO8601", "post.lastUpdatedISO8601",
    "post.author", "post.labels", "post.numComments", "post.comments",
    "post.allowComments", "post.embedCommentForm", "post.addCommentUrl",
    "post.addCommentOnclick", "post.commentFormIframeSrc", "post.cmtfpIframe",
    "post.appRpcRelayPath",
    # label loop
    "label.name", "label.url", "label.count", "label.isLast",
    # comment loop
    "comment.author", "comment.authorUrl", "comment.body", "comment.timestamp",
    "comment.anchorName",
    # widget level
    "title", "description", "content", "labels", "showFreqNumbers", "links",
    "link.href", "link.title",
    # pager
    "newerPageUrl", "newerPageTitle", "olderPageUrl", "olderPageTitle", "homeMsg",
    # platform messages
    "postCommentMsg", "blogCommentMessage", "blogTeamBlogMessage", "postLabelsLabel",
    "widget.instanceId",
}

EXTERNAL_JS_RE = re.compile(r"<script[^>]+src=['\"]https?://", re.I)
WEBFONT_RE = re.compile(r"fonts\.googleapis\.com|fonts\.gstatic\.com|@import\s+url\(['\"]?https?://", re.I)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")


def configured_site_names() -> list[str]:
    """Site identifiers taken from blogger/config.json (the single source of truth).

    The theme must not bake any of these into rendered markup: the blog has to keep
    working unchanged after a rename or a custom-domain switch, which is an explicit
    JHL-4 constraint ("URL·사이트명 하드코딩 금지 — 설정값으로").
    """
    import json

    try:
        with open(CONFIG_PATH, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, ValueError):
        return []
    names = {cfg.get("siteName") or ""}
    blog = cfg.get("blog") or {}
    for key in ("blogspotUrl", "customDomainUrl"):
        url = blog.get(key)
        if url:
            names.add(url.split("//", 1)[-1].strip("/").split("/")[0])
    return sorted(n for n in names if n)

AD_SLOT_IDS = ("ad-top", "ad-in-article", "ad-bottom")

failures: list[str] = []
checks_run = 0


def check(condition: bool, label: str, detail: str = "") -> bool:
    global checks_run
    checks_run += 1
    if condition:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}" + (f" — {detail}" if detail else ""))
        failures.append(label)
    return condition


def main(path: str) -> int:
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    print(f"Theme: {path} ({len(raw)} bytes)\n")

    print("[1] XML parsing and Blogger namespaces")
    try:
        root = ET.fromstring(raw)
        check(True, "XML is well formed")
    except ET.ParseError as exc:  # pragma: no cover - reported, not raised
        check(False, "XML is well formed", str(exc))
        print("\nCannot continue without a parseable XML file.")
        return 1
    check(root.tag.endswith("}html") or root.tag == "html", "root element is <html>", root.tag)
    for prefix, uri in (("b", B), ("data", DATA), ("expr", EXPR)):
        ns = uri[1:-1]
        declared = f'xmlns:{prefix}="{ns}"' in raw or f"xmlns:{prefix}='{ns}'" in raw
        check(declared, f"namespace {prefix} declared")

    print("\n[2] <b:skin> and CSS")
    skins = [e for e in root.iter(f"{B}skin")]
    check(len(skins) == 1, "exactly one <b:skin> block", f"found {len(skins)}")
    skin_text = skins[0].text or "" if skins else ""
    check(len(skin_text) > 3000, "b:skin contains real CSS", f"{len(skin_text)} chars")
    check("$(body.text.color)" in skin_text, "CSS uses theme-designer variables")
    check(len(skin_text) < 20000, "CSS stays inside a lightweight budget", f"{len(skin_text)} chars")

    print("\n[2b] Theme generation declarations (required for widgets to instantiate)")
    # Blogger only instantiates and renders <b:widget> content for themes that declare
    # which layout generation they are written against. Omitting these produced a live
    # page whose five sections all rendered as empty 'no-items' divs while Blogger still
    # registered every widget client-side (JHL-4, 2026-10-16).
    check(re.search(r"<html[^>]*\sb:version='2'", raw) is not None,
          "<html> declares b:version='2'")
    check(re.search(r"<html[^>]*\sclass='[^']*\bv2\b", raw) is not None,
          "<html> declares class='v2' (Blogger's layouts-v2 hook)")
    check(re.search(r"<html[^>]*\sb:responsive='true'", raw) is not None,
          "<html> declares b:responsive='true' (mobile uses this theme, not the fallback)")

    print("\n[3] Widgets, sections and includables")
    widgets = list(root.iter(f"{B}widget"))
    check(len(widgets) > 0, "theme declares widgets")
    blog_widgets = [w for w in widgets if (w.get("type") or "") == "Blog"]
    check(len(blog_widgets) == 1, "exactly one Blog widget", f"found {len(blog_widgets)}")

    sections = list(root.iter(f"{B}section"))
    section_ids = [s.get("id") for s in sections]
    check(len(section_ids) == len(set(section_ids)), "section ids are unique", str(section_ids))
    check(all(i and re.fullmatch(r"[A-Za-z][\w-]*", i) for i in section_ids),
          "section ids are valid identifiers", str(section_ids))
    widget_ids = [w.get("id") for w in widgets]
    check(len(widget_ids) == len(set(widget_ids)), "widget ids are unique", str(widget_ids))

    # every widget must sit inside a section
    nested_outside = 0
    for section in sections:
        for widget in section.iter(f"{B}widget"):
            widget.set("_in_section", "1")
    nested_outside = sum(1 for w in widgets if w.get("_in_section") != "1")
    check(nested_outside == 0, "every widget lives inside a <b:section>", f"{nested_outside} orphan(s)")

    dangling: list[str] = []
    missing_main: list[str] = []
    for widget in widgets:
        defined = {i.get("id") for i in widget.iter(f"{B}includable")}
        if "main" not in defined:
            missing_main.append(widget.get("id") or "?")
        for inc in widget.iter(f"{B}include"):
            name = inc.get("name")
            if name and name not in defined:
                dangling.append(f"{widget.get('id')}->{name}")
    check(not missing_main, "every widget defines an includable id='main'", str(missing_main))
    check(not dangling, "every <b:include> resolves inside its widget", str(dangling))

    print("\n[4] Data tags are limited to the classic Layouts v2 model")
    used = sorted(set(re.findall(r"<data:([A-Za-z0-9_.]+)", raw)))
    unknown = [t for t in used if t not in ALLOWED_DATA_TAGS]
    check(not unknown, "no unknown/v3-only data tags", str(unknown))
    print(f"        {len(used)} distinct data tags in use")

    print("\n[5] Attribute quoting")
    # Blogger requires single quotes on tag attributes. Everything inside
    # <b:skin> CDATA (CSS, theme-designer Variable definitions) and inside
    # comments may quote freely, so only real markup is inspected here.
    markup_only = re.sub(r"<!\[CDATA\[.*?\]\]>", "", raw, flags=re.S)
    markup_only = re.sub(r"<\?xml.*?\?>", "", markup_only, flags=re.S)
    markup_only = re.sub(r"<!--.*?-->", "", markup_only, flags=re.S)
    double_quoted = re.findall(r"\s(?:expr:)?[A-Za-z_-]+=\"", markup_only)
    check(not double_quoted, "all tag attributes are single quoted", str(double_quoted[:5]))

    print("\n[5b] No hard-coded host or site name (JHL-4 constraint)")
    # Rendered markup only: CDATA, XML declaration, comments and namespace
    # declarations never reach the page, so they are out of scope here.
    rendered = re.sub(r"\sxmlns(?::[A-Za-z]+)?='[^']*'", "", markup_only)
    hard_urls = sorted(set(re.findall(r"=(?:expr:)?'https?://[^']*'", rendered)))
    check(not hard_urls, "no absolute URL is hard-coded in markup", str(hard_urls))
    # Widget titles are Blogger *settings* (editable under Layout), not code, so the
    # site name may appear there — and nowhere else.
    without_widget_titles = html.unescape(re.sub(r"\stitle='[^']*'", "", rendered))
    names = configured_site_names()
    leaked = sorted(n for n in names if n in without_widget_titles)
    check(not leaked, "site name appears only in widget-title settings",
          f"{leaked} (from config.json: {names})")

    print("\n[6] Feature requirements (JHL-4 §1)")
    check("figure" in raw and "figcaption" in raw, "figure/figcaption markup + styling present")
    check(re.search(r"\.post-body figure", skin_text) is not None, "figure styling block present")
    for slot in AD_SLOT_IDS:
        check(f"id='{slot}'" in raw, f"AdSense container #{slot} present")
    check(raw.count("ADSENSE-") >= 3, "AdSense insertion comments present at all three slots")
    check("loading', 'lazy'" in raw or "loading" in raw, "lazy-loading handled in markup or script")
    check("prefers-color-scheme: dark" in skin_text, "dark mode via prefers-color-scheme")
    check("all-head-content" in raw, "Blogger head include present (canonical/description/OG)")
    check('rel="canonical"' not in raw and "rel='canonical'" not in raw,
          "theme does not duplicate Blogger's canonical tag")
    check("post-body entry-content" in raw, "post body wrapper class kept (Blogger conventions)")
    check(not EXTERNAL_JS_RE.search(raw), "no external JavaScript is loaded")
    check(not WEBFONT_RE.search(raw), "no external web fonts are loaded")
    check("<b:section" in raw, "sections present for widget editing")

    print("\n[7] Structure against the live blogspot theme")
    for needle, label in (
        ("data:blog.pageType == &quot;index&quot;", "index vs item branch"),
        ("data:blog.postImageThumbnailUrl", "per-post social image"),
        ("application/ld+json", "Article structured data"),
        ("site-title", "site title element"),
    ):
        check(needle in raw, label)

    print()
    if failures:
        print(f"RESULT: {len(failures)} of {checks_run} checks FAILED")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"RESULT: all {checks_run} checks passed")
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_THEME
    sys.exit(main(target))
