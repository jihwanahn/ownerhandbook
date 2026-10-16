#!/usr/bin/env python3
"""Derive the 'declaration generation' variant of a Blogger theme XML.

Why this exists (JHL-4, 2026-10-17)
-----------------------------------
The live blog serves our theme but Blogger instantiates **none** of its widgets:
every section comes back as an empty `no-items` div while the layout still holds
widget instances. The chief-of-staff hypothesis under test is that our widget
*declarations* are one generation behind the layout Blogger created for this
blog (2026):

    our file   : <html b:version='2' b:responsive='true' class='v2'>   (no b:defaultwidgetversion)
                 all 8 widgets declare version='1', no visible='', sections have no name=''
    vtrick 1.9.0: <html b:css='false' b:defaultwidgetversion='2' b:layoutsVersion='3'>
                 all widgets declare version='2' visible='true', sections carry name=''

So this script rewrites **declarations only** — never the CSS, the includables,
the data tags, the ad slots or the widget settings. That keeps the experiment
falsifiable: if the variant fails on the blog, exactly one variable moved.

    <html>      : add b:defaultwidgetversion='2'
                  (b:version='2', class='v2', b:responsive='true' stay; so does the
                   absence of b:layoutsVersion='3', which is a v3-only token and would
                   break the v2-model data tags this theme uses)
    <b:widget>  : version='2' visible='true'
    <b:section> : name='Header' / 'Navigation' / 'Posts' / 'Sidebar' / 'Footer'

Edits are text-level (tag attributes), not a re-serialisation, so the diff against
the source file stays a handful of attribute changes and nothing else can drift.

Usage:
    python blogger/theme/decl_variant.py                    # rewrite the variant file
    python blogger/theme/decl_variant.py --check            # fail if it is stale
    python blogger/theme/decl_variant.py --stdout           # print, do not write
Exit code 0 = variant on disk matches the source file's declarations.
"""

from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "owners-handbook-v1.xml")
TARGET = os.path.join(HERE, "owners-handbook-v2-decl.xml")

DEFAULT_WIDGET_VERSION = "2"

# Blogger shows these names in the Layout screen; naming sections is what modern
# themes do and it keeps the Layout UI readable for the owner.
SECTION_NAMES = {
    "header": "Header",
    "nav": "Navigation",
    "main-posts": "Posts",
    "sidebar": "Sidebar",
    "footer": "Footer",
}

# Attributes that carry the declaration generation. Everything else in the file
# must stay byte-identical between the source theme and its variant.
DECLARATION_ATTRS = (
    r"\sb:version='[^']*'",
    r"\sb:defaultwidgetversion='[^']*'",
    r"\sb:responsive='[^']*'",
    r"\sb:css='[^']*'",
    r"\sb:layoutsVersion='[^']*'",
    r"<html\s+class='[^']*'",
)
WIDGET_DECL_ATTRS = (r"\sversion='[^']*'", r"\svisible='[^']*'")
SECTION_DECL_ATTRS = (r"\sname='[^']*'",)

WIDGET_TAG = re.compile(r"<b:widget\s[^>]*>")
SECTION_TAG = re.compile(r"<b:section\s[^>]*>")
HTML_TAG = re.compile(r"<html\s[^>]*>")


def _with_attribute(tag: str, attr: str, value: str) -> str:
    """Return `tag` with attr='value' set, replacing an existing value in place."""
    pattern = re.compile(rf"\s{attr}='[^']*'")
    if pattern.search(tag):
        return pattern.sub(f" {attr}='{value}'", tag, count=1)
    return tag[:-1] + f" {attr}='{value}'>"


def _rewrite_html(match: re.Match) -> str:
    tag = match.group(0)
    if "b:defaultwidgetversion=" in tag:
        return tag
    if not re.search(r"\sb:version='", tag):
        raise ValueError("<html> must declare b:version before the variant is derived")
    return re.sub(r"(\sb:version='[^']*')", rf"\1 b:defaultwidgetversion='{DEFAULT_WIDGET_VERSION}'",
                  tag, count=1)


def _rewrite_widget(match: re.Match) -> str:
    tag = _with_attribute(match.group(0), "version", DEFAULT_WIDGET_VERSION)
    return _with_attribute(tag, "visible", "true")


def _rewrite_section(match: re.Match) -> str:
    tag = match.group(0)
    sid = re.search(r"\sid='([^']*)'", tag)
    if not sid:
        raise ValueError(f"<b:section> without id: {tag}")
    try:
        name = SECTION_NAMES[sid.group(1)]
    except KeyError:  # pragma: no cover - explicit failure beats a silent default
        raise ValueError(
            f"section id '{sid.group(1)}' has no declared Layout name; "
            f"add it to SECTION_NAMES (known: {sorted(SECTION_NAMES)})"
        ) from None
    return _with_attribute(tag, "name", name)


def derive(raw: str) -> tuple[str, dict[str, int]]:
    """Return the declaration variant of `raw` plus a count report."""
    widgets = len(WIDGET_TAG.findall(raw))
    sections = len(SECTION_TAG.findall(raw))
    out = HTML_TAG.sub(_rewrite_html, raw, count=1)
    out = WIDGET_TAG.sub(_rewrite_widget, out)
    out = SECTION_TAG.sub(_rewrite_section, out)
    return out, {"widgets": widgets, "sections": sections}


def strip_declarations(raw: str) -> str:
    """Remove every declaration-generation attribute, for the 'nothing else moved' proof."""
    out = raw
    for pattern in DECLARATION_ATTRS + WIDGET_DECL_ATTRS + SECTION_DECL_ATTRS:
        out = re.sub(pattern, "", out)
    return out


def main(argv: list[str]) -> int:
    with open(SOURCE, encoding="utf-8") as fh:
        source = fh.read()
    variant, report = derive(source)

    if "--stdout" in argv:
        sys.stdout.write(variant)
        return 0

    if "--check" in argv:
        try:
            with open(TARGET, encoding="utf-8") as fh:
                existing = fh.read()
        except OSError:
            print(f"STALE: {os.path.basename(TARGET)} is missing")
            return 1
        if existing != variant:
            print(f"STALE: {os.path.basename(TARGET)} differs from a fresh derivation of "
                  f"{os.path.basename(SOURCE)}")
            return 1
        if strip_declarations(existing) != strip_declarations(source):
            print("STALE: the variant changes something other than declarations")
            return 1
        print(f"OK: {os.path.basename(TARGET)} == declarations-only derivation of "
              f"{os.path.basename(SOURCE)} ({report['widgets']} widgets, "
              f"{report['sections']} sections)")
        return 0

    with open(TARGET, "w", encoding="utf-8", newline="") as fh:
        fh.write(variant)
    print(f"wrote {TARGET} ({len(variant)} bytes) from {os.path.basename(SOURCE)}")
    print(f"  widgets version={DEFAULT_WIDGET_VERSION} visible=true : {report['widgets']}")
    print(f"  sections named ({', '.join(SECTION_NAMES.values())}) : {report['sections']}")
    print("  everything else byte-identical "
          "(CSS, includables, data tags, ad slots, widget settings)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))