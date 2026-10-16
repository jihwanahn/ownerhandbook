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
    0  theme v1 is live, its widgets render, and its SEO tags are correct
    1  theme v1 is live but something is wrong with the SEO output
    4  theme v1 is live but its widgets do not render (every section is an empty
       'no-items' div) — the blog's layout has not been rebuilt against the theme
    5  the theme serves desktop but Blogger's stock template still serves ?m=1
       (mobile-first requirement)
    3  the current theme file is not what the blog serves: the page is either still on a
       stock theme, or on an older generation of ours (see check [1b])
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

# Blogger's own mobile fallback template, served on ?m=1 until the theme declares
# b:responsive='true'. These section ids exist only in that stock template.
STOCK_MOBILE_SECTIONS = [
    (r"id=['\"]navbar['\"]", "stock mobile navbar section"),
    (r"id=['\"]crosscol['\"]", "stock mobile crosscol section"),
]

# The rendered <html> element. Blogger strips the b: attributes and keeps class, so the
# class tokens on the live element are the only place the theme's generation is visible
# from outside. Counting them inside comments gives a false positive: our theme's own
# header comment quotes `class='v2'` while explaining the declaration, and my first
# probe today read exactly that comment and reported the declaration as live.
HTML_TAG_RE = re.compile(r"<html\b[^>]*>", re.I)
CLASS_ATTR_RE = re.compile(r"\bclass=['\"]([^'\"]*)['\"]")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)

THEME_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "owners-handbook-v1.xml")

# Blogger wraps each instantiated widget in <div class='widget <Type>' ... id='<WidgetId>'>
# and, at the end of <body>, registers every widget it rendered. When a theme's widgets are
# never instantiated the page contains the registration script but no wrapper elements at
# all, and each section closes as  <div class='... no-items section' id='...'></div>.
WIDGET_WRAPPER_RE = re.compile(r"<div[^>]*\bclass=['\"][^'\"]*\bwidget\b[^'\"]*['\"][^>]*\bid=['\"]([^'\"]+)['\"]")
REGISTER_RE = re.compile(r"_RegisterWidget\('_\w+',\s*new _WidgetInfo\('([^']+)',\s*'([^']+)'")
EMPTY_SECTION_RE = re.compile(
    r"<div[^>]*\bclass=['\"][^'\"]*\bno-items\b[^'\"]*['\"][^>]*\bid=['\"]([^'\"]+)['\"][^>]*>\s*</div>")
SCRIPT_RE = re.compile(r"<script\b.*?</script>", re.S | re.I)
WIDGET_DECL_RE = re.compile(r"<b:widget\s+id='([^']+)'")
SECTION_DECL_RE = re.compile(r"<b:section[^>]*\sid='([^']+)'")


def theme_declarations() -> tuple[list[str], list[str]]:
    """Widget ids and section ids the theme file declares (offline, same repo)."""
    try:
        with open(THEME_FILE, encoding="utf-8") as fh:
            raw = fh.read()
    except OSError:
        return [], []
    return WIDGET_DECL_RE.findall(raw), SECTION_DECL_RE.findall(raw)


def theme_generation_tokens() -> set[str]:
    """Class tokens the theme file declares on its own <html> element (e.g. {'v2'})."""
    try:
        with open(THEME_FILE, encoding="utf-8") as fh:
            raw = fh.read()
    except OSError:
        return set()
    tag = HTML_TAG_RE.search(COMMENT_RE.sub("", raw))
    if not tag:
        return set()
    class_attr = CLASS_ATTR_RE.search(tag.group(0))
    return set(class_attr.group(1).split()) if class_attr else set()


def live_generation_tokens(html_text: str) -> set[str]:
    """Class tokens on the <html> element Blogger actually served, comments ignored.

    The element itself, never the theme's comments: a page can carry our theme's comment
    saying `class='v2'` while the element rendered from an older file has no class at all.
    """
    tag = HTML_TAG_RE.search(COMMENT_RE.sub("", html_text))
    if not tag:
        return set()
    class_attr = CLASS_ATTR_RE.search(tag.group(0))
    return set(class_attr.group(1).split()) if class_attr else set()



def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", "replace")


def report(html_text: str, url: str, mobile_html: str | None = None) -> int:
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

    print("\n[1b] Theme generation in the rendered page")
    # "The theme is live" and "the *current* theme file is live" are different questions.
    # The owner saves by hand, so a paste can silently not land, or land as an older copy;
    # the class tokens on the served <html> element are the only outside evidence of which
    # generation is up. Blogger strips the b: attributes, so `class='v2'` is the marker.
    declared_tokens = theme_generation_tokens()
    live_tokens = live_generation_tokens(html_text)
    missing_tokens = sorted(declared_tokens - live_tokens)
    if not declared_tokens:
        generation_current = None
        print("  theme file declares no <html> class — nothing to compare (skip)")
    else:
        generation_current = not missing_tokens
        print(f"  theme file declares : class='{' '.join(sorted(declared_tokens))}'")
        if live_tokens:
            print(f"  live <html> carries : class='{' '.join(sorted(live_tokens))}'")
        else:
            print("  live <html> carries : no class attribute at all")
        if generation_current:
            print("  PASS  the served page is the current theme generation")
        else:
            print("  FAIL  the blog is serving an older generation of the theme"
                  f" (missing: {', '.join(missing_tokens)})")

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

    print("\n[5] Widget rendering (the live layout has to be instantiated)")
    # "The theme is live" and "the theme's widgets render" are different questions: a page
    # can pass every SEO check above while all five sections render as empty divs.
    # Scripts are stripped first because Blogger registers every widget inside one.
    declared_widgets, declared_sections = theme_declarations()
    markup = SCRIPT_RE.sub("", html_text)
    rendered = set(WIDGET_WRAPPER_RE.findall(markup))
    registered = REGISTER_RE.findall(html_text)
    registered_ids = [wid for wid, _ in registered]
    empty_sections = [sid for sid in EMPTY_SECTION_RE.findall(markup) if sid in declared_sections]
    unrendered = [wid for wid in (registered_ids or declared_widgets) if wid not in rendered]

    print(f"  theme declares {len(declared_widgets)} widget(s) in {len(declared_sections)} section(s)")
    print(f"  Blogger registered {len(registered_ids)} widget(s) client-side")
    for wid in declared_widgets:
        state = "RENDERED" if wid in rendered else (
            "REGISTERED BUT EMPTY" if wid in registered_ids else "NOT INSTANTIATED")
        print(f"    {state:22} {wid}")
    print(f"  widget wrappers found in the page: {len(rendered)}")
    for sid in empty_sections:
        print(f"  EMPTY SECTION          #{sid} (rendered as <div class='... no-items section'>)")

    widget_failures: list[str] = []
    if empty_sections:
        widget_failures.append(f"{len(empty_sections)} section(s) rendered empty: {empty_sections}")
    if unrendered:
        widget_failures.append(f"{len(unrendered)} widget(s) produced no markup: {unrendered}")
    if not widget_failures:
        print("  PASS  every declared widget produced markup")

    print("\n[6] Mobile slot (mobile-first: the theme must serve ?m=1)")
    mobile_failures: list[str] = []
    if mobile_html is None:
        print("  SKIP  no mobile page fetched")
    else:
        mobile_markers = [label for pattern, label in THEME_MARKERS
                          if re.search(pattern, mobile_html, re.I)]
        stock_markers = [label for pattern, label in STOCK_MOBILE_SECTIONS
                         if re.search(pattern, mobile_html, re.I)]
        if stock_markers:
            mobile_failures.append("?m=1 is served by Blogger's stock template: "
                                   + ", ".join(stock_markers))
            print("  FAIL  ?m=1 still runs Blogger's stock template — the theme's")
            print("        b:responsive='true' declaration is not in effect, so mobile")
            print("        readers never see the theme (and its SEO tags).")
        elif len(mobile_markers) < len(THEME_MARKERS):
            mobile_failures.append(f"?m=1 shows only {len(mobile_markers)}/{len(THEME_MARKERS)}"
                                   " theme markers")
            print(f"  FAIL  ?m=1 shows only {len(mobile_markers)}/{len(THEME_MARKERS)}"
                  " theme markers")
        else:
            print("  PASS  ?m=1 serves this theme (not the stock mobile template)")

    problems = seo_failures + duplicates
    print()
    if widget_failures:
        print("RESULT: the theme is live, but its widgets do not render — the sections are empty.")
        print("        Sections render when the blog's layout holds a widget instance for them;")
        print("        an empty 'no-items' div means it does not. In this order:")
        print("          1. Blogger -> Layout: confirm the widget boxes exist, then click")
        print("             'Save arrangement' (정렬 저장) once.")
        if generation_current:
            print("          2. Apply blogger/theme/owners-handbook-v2-decl.xml — the declaration-")
            print("             only variant of the live file (b:defaultwidgetversion='2', every")
            print("             widget version='2' visible='true', named sections). Upload it, or")
            print("             paste it exactly like before.")
            print("             (Re-pasting owners-handbook-v1.xml changes nothing — the served")
            print("             page already is that file, check [1b].)")
            print("          3. Still empty? Paste blogger/theme/bisect/B0-baseline.xml (see its")
            print("             PLAN.md): a 3-section/3-widget theme that separates 'this theme'")
            print("             from 'this blog'.")
            print("          4. If B0 renders its widgets, bisect this theme's blocks (PLAN.md")
            print("             step 4); if it does not, the layout is the problem, not the file.")
        else:
            print("          2. Re-apply the current theme file (Edit HTML -> replace all ->")
            print("             Save) — the served page is an older generation (check [1b]).")
            print("          3. Still empty? Paste blogger/theme/bisect/B0-baseline.xml (see its")
            print("             PLAN.md) to prove whether any custom theme can render widgets here.")
        for f in widget_failures:
            print(f"        - {f}")
        return 4
    if generation_current is False:
        print("RESULT: theme v1 is live and rendering, but the served page is an older")
        print("        generation than the file in this repo (check [1b]), so the latest fixes")
        print("        are not live yet. Re-apply blogger/theme/owners-handbook-v1.xml")
        print("        (blogger/theme/UPLOAD-GUIDE.md) and re-run this script.")
        return 3
    if mobile_failures:
        print("RESULT: desktop is fine, but the mobile-first requirement is not met:")
        for f in mobile_failures:
            print(f"  - {f}")
        print("        Re-apply the theme file: its <html> carries")
        print("        b:responsive='true', which is what moves the ?m=1 slot to the theme.")
        return 5
    if problems:
        print("RESULT: theme v1 is live, but these checks failed:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("RESULT: theme v1 is live and its SEO tags are correct")
    return 0


def mobile_url(url: str) -> str:
    """The same page as Blogger's mobile slot serves it (?m=1).

    Our theme declares b:responsive='true', which is what makes Blogger use the theme for
    the mobile slot instead of its stock mobile template; before that declaration this
    blog served a stock template with different sections and Korean UI strings on ?m=1.
    """
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}m=1"


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
    try:
        mobile_html = fetch(mobile_url(args.url))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"Could not fetch the mobile copy ({mobile_url(args.url)}): {exc}"
              " — skipping check [6]")
        mobile_html = None
    return report(html_text, args.url, mobile_html)


if __name__ == "__main__":
    sys.exit(main())
