#!/usr/bin/env python3
"""Derive the Layouts v3 variants of the Blogger theme XML.

Why this exists (JHL-4, 2026-10-18)
-----------------------------------
The live blog serves our theme but Blogger instantiates none of its widgets: five
sections render as empty `no-items` divs while the layout registrations are built
from our own sections. Every theme we have observed rendering widgets — Blogger's
own stock templates and every working third-party theme — declares the *Layouts v3*
surface on `<html>`:

    vtrick 1.9.0  : <html b:css='false' b:defaultwidgetversion='2' b:layoutsVersion='3' ...>
    tech-jet 2.8.2: <html b:css='false' b:defaultwidgetversion='2' b:js='true' b:layoutsVersion='3' ...>
    jobzeek       : <html b:css='false' b:defaultwidgetversion='2' b:js='true' b:layoutsVersion='3' ...>
    ours          : <html b:version='2' b:defaultwidgetversion='2' b:responsive='true' class='v2' ...>

Ours is the only one missing `b:layoutsVersion='3'`, and the only one whose widgets
never render. All three working themes also declare `<b:defaultmarkups>` in `<head>`
with one block per widget type — in vtrick 16 of the 17 blocks are *empty* (only
`Common` carries shared includables), which is what a theme that supplies each
widget's own includables inline needs.

Two files are generated, one variable at a time, so a failure stays attributable:

    owners-handbook-v3-decl.xml   v2-decl + b:layoutsVersion='3' + <b:defaultmarkups>
                                  (declaration surface only — data tags stay v2)
    owners-handbook-v3-tags.xml   the above + every data tag moved to the v3 model

The tag mapping is grounded, not invented: each right-hand token is one that appears
in the working v3 themes above (see TAG_MAP evidence column). Tokens with no grounded
counterpart are replaced with literal text instead of a guessed tag.

Usage:
    python blogger/theme/v3_variant.py            # (re)write both variant files
    python blogger/theme/v3_variant.py --check    # fail if either is stale
    python blogger/theme/v3_variant.py --stdout   # print the declaration variant
Exit code 0 = both variants on disk match a fresh derivation.
"""

from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "owners-handbook-v2-decl.xml")
DECL_TARGET = os.path.join(HERE, "owners-handbook-v3-decl.xml")
TAGS_TARGET = os.path.join(HERE, "owners-handbook-v3-tags.xml")

LAYOUTS_VERSION = "3"

# Widget-type surface declared by working v3 themes (vtrick 1.9.0, verbatim order).
# Every block is emitted empty: this theme supplies every widget's includables inline
# inside <b:widget>, so the defaults only have to exist, not to carry markup.
DEFAULT_MARKUP_TYPES = (
    "Common", "Header", "LinkList", "TextList", "HTML", "Text", "Blog",
    "PopularPosts", "FeaturedPost", "ContactForm", "Label", "FollowByEmail",
    "Image", "BlogArchive", "PageList", "BlogSearch", "Profile",
)

DEFAULT_MARKUPS_BLOCK = (
    "\n<!--\n"
    "  Layouts v3 widget-type surface. Every working v3 theme declares these blocks;\n"
    "  in vtrick 1.9.0 (a live third-party theme) 16 of the 17 are empty and only\n"
    "  'Common' carries shared includables. Every widget in this theme supplies its own\n"
    "  includables inside <b:widget>, so the blocks below are intentionally empty —\n"
    "  they declare which widget types this theme knows about, nothing else.\n"
    "-->\n"
    "<b:defaultmarkups>\n"
    + "".join(f"  <b:defaultmarkup type='{t}'>\n  </b:defaultmarkup>\n" for t in DEFAULT_MARKUP_TYPES)
    + "</b:defaultmarkups>\n"
)

# ---------------------------------------------------------------- tag mapping
# (pattern, replacement, why). Order matters: the specific conditions are rewritten
# before the bare tokens they contain.
TAG_MAP: tuple[tuple[str, str, str], ...] = (
    (r"data:blog\.pageType == &quot;index&quot;", "data:view.isMultipleItems",
     "vtrick/jobzeek: data:view.isMultipleItems (index = home, label, archive)"),
    (r"data:blog\.pageType == &quot;item&quot;", "data:view.isPost",
     "vtrick/jobzeek: data:view.isPost"),
    (r"data:blog\.url == data:blog\.homepageUrl", "data:view.isHomepage",
     "vtrick/jobzeek: data:view.isHomepage"),
    (r"data:blog\.homepageUrl != data:blog\.url", "!data:view.isHomepage",
     "vtrick/jobzeek: data:view.isHomepage"),
    (r"data:blog\.url", "data:view.url.canonical",
     "vtrick: canonical link is data:view.url.canonical in v3"),
    (r"data:blog\.pageName", "data:view.title",
     "jobzeek: data:view.title"),
    (r"<data:blog\.postImageThumbnailUrl/>",
     "<b:eval expr='resizeImage(data:widgets.Blog.first.posts[0].featuredImage, "
     "1200, &quot;1200:630&quot;)'/>",
     "vtrick: resizeImage(data:post.featuredImage, 1200, \"1200:630\") — and the token form "
     "data:widgets.Blog.first.posts[0].featuredImage cannot be an element name ([ ] are "
     "illegal in XML names), so it has to be evaluated"),
    (r"data:blog\.postImageThumbnailUrl", "data:widgets.Blog.first.posts[0].featuredImage",
     "vtrick og:image: data:widgets.Blog.first.posts[0].featuredImage"),
    (r"data:post\.timestampISO8601", "data:post.date.iso8601",
     "vtrick: <time expr:datetime='data:post.date.iso8601'>"),
    (r"data:post\.lastUpdatedISO8601", "data:post.lastUpdated.iso8601",
     "jobzeek: data:post.lastUpdated.iso8601"),
    (r"data:post\.timestamp", "data:post.date",
     "vtrick: <data:post.date/>"),
    (r"data:post\.author", "data:post.author.name",
     "vtrick/jobzeek: data:post.author.name"),
    (r"data:post\.numComments", "data:post.numberOfComments",
     "vtrick: data:post.numberOfComments"),
    # Snippets: every working v3 theme wraps them in the snippet()/snippet-operator form,
    # never a bare `data:post.snippets.long` tag, so both rewrite sites follow that shape.
    (r"expr:content='data:post\.snippet'",
     "expr:content='snippet(data:post.snippets.long, { length: 160 })'",
     "jobzeek: <b:eval expr='snippet(data:post.snippets.long, { length: 500 })'/>"),
    (r"<data:post\.snippet/>",
     "<b:eval expr='snippet(data:post.snippets.long, { length: 300 })'/>",
     "jobzeek: <b:eval expr='snippet(data:post.snippets.long, { length: 500 })'/>"),
    (r"data:newerPageTitle", "data:messages.newer",
     "vtrick: data:messages.newer"),
    (r"data:olderPageTitle", "data:messages.older",
     "vtrick: data:messages.older"),
    (r"data:postCommentMsg", "data:messages.postAComment",
     "vtrick/jobzeek: data:messages.postAComment"),
    (r"<data:postLabelsLabel/>", "Filed under:",
     "no grounded v3 counterpart — literal text instead of a guessed tag"),
    (r"<data:blogCommentMessage/>",
     "Comments are moderated. Corrections and questions are welcome.",
     "no grounded v3 counterpart — literal text instead of a guessed tag"),
    (r"<data:blogTeamBlogMessage/>", "Comments are moderated.",
     "no grounded v3 counterpart — literal text instead of a guessed tag"),
)

# Tokens that only the v2 data model defines (or whose meaning changed in v3) — the
# tags variant must not contain any of them. Escaped into patterns for the check.
V2_ONLY_TOKENS = (
    "blog.pageType", "blog.pageName", "blog.url", "blog.postImageThumbnailUrl",
    "post.timestampISO8601", "post.timestamp", "post.lastUpdatedISO8601",
    "post.author", "post.numComments", "post.snippet",
    "newerPageTitle", "olderPageTitle", "postCommentMsg",
    "blogCommentMessage", "blogTeamBlogMessage", "postLabelsLabel",
)
V2_ONLY_PATTERNS = tuple(r"data:" + re.escape(t) + r"(?![\w.])" for t in V2_ONLY_TOKENS)

# Literal text used where no grounded v3 counterpart exists (never a guessed tag).
LITERAL_REPLACEMENTS = (
    "Filed under:",
    "Comments are moderated. Corrections and questions are welcome.",
    "Comments are moderated.",
)

# Tokens the v3 model adds that this theme starts using.
V3_TOKENS_USED = (
    "view.isMultipleItems", "view.isPost", "view.isHomepage", "view.title",
    "view.url.canonical", "widgets.Blog.first.posts[0].featuredImage",
    "post.date.iso8601", "post.date", "post.lastUpdated.iso8601",
    "post.author.name", "post.numberOfComments", "post.snippets.long",
    "messages.newer", "messages.older", "messages.postAComment",
)

TAGS_HEADER_NOTE = (
    "  LAYOUTS v3 DECLARATION VARIANT (owners-handbook-v3-decl.xml), generated by\n"
    "  v3_variant.py from owners-handbook-v2-decl.xml: <html> gains b:layoutsVersion='3'\n"
    "  and <head> gains <b:defaultmarkups> (one empty block per widget type that a working\n"
    "  v3 theme declares). Nothing else moved — the data tags stay v2 on purpose, because\n"
    "  this file isolates the declaration surface. owners-handbook-v3-tags.xml is the same\n"
    "  file with the data model moved to v3 (see TAG_MAP in v3_variant.py for the evidence).\n"
    "  The comment thread includables keep the classic comment-thread loop: no v3 theme we\n"
    "  could check uses it, but nothing renders it while this blog has 0 posts, so it stays\n"
    "  until Blogger's validator names it.\n"
    "  DATA MODEL: v2 (deliberate probe)\n"
)

TAGS_MODEL_LINE = "  DATA MODEL: v2 (deliberate probe)\n"
TAGS_MODEL_V3_LINE = "  DATA MODEL: v3\n"

HEADER_ANCHOR = "  ==================================================================\n"

HTML_TAG = re.compile(r"<html\s[^>]*>")
SKIN_END = re.compile(r"\]\]></b:skin>")
XML_DECL = re.compile(r"<\?xml[^>]*\?>\s*")
DECL_ATTRS = (r"\sb:layoutsVersion='[^']*'",)
DATA_TOKEN = re.compile(r"&lt;data:[A-Za-z0-9_.]+|</?data:[A-Za-z0-9_.]+")


def _add_layouts_version(raw: str) -> str:
    def repl(match: re.Match) -> str:
        tag = match.group(0)
        if re.search(r"\sb:layoutsVersion=", tag):
            return tag
        if not re.search(r"\sb:defaultwidgetversion='", tag):
            raise ValueError(
                "<html> must already declare b:defaultwidgetversion before the v3 "
                "variant is derived"
            )
        return re.sub(
            r"(\sb:defaultwidgetversion='[^']*')",
            rf"\1 b:layoutsVersion='{LAYOUTS_VERSION}'",
            tag,
            count=1,
        )

    out, n = HTML_TAG.subn(repl, raw, count=1)
    if n != 1:
        raise ValueError("no <html> tag found")
    return out


def _insert_default_markups(raw: str) -> str:
    if "<b:defaultmarkups>" in raw:
        return raw
    out, n = SKIN_END.subn(lambda m: m.group(0) + DEFAULT_MARKUPS_BLOCK, raw, count=1)
    if n != 1:
        raise ValueError("no ']]></b:skin>' found — cannot place <b:defaultmarkups>")
    return out


def derive_declaration_variant(raw: str) -> str:
    """Layouts v3 declaration surface only (data tags stay v2 — one variable)."""
    out = _add_layouts_version(raw)
    out = _insert_default_markups(out)
    return _insert_header_note(out)


def _insert_header_note(raw: str) -> str:
    if TAGS_HEADER_NOTE in raw:
        return raw
    if HEADER_ANCHOR not in raw:
        raise ValueError("theme header banner not found — cannot document the variant")
    return raw.replace(HEADER_ANCHOR, HEADER_ANCHOR + TAGS_HEADER_NOTE, 1)


def tag_substitutions(raw: str) -> tuple[str, dict[str, int]]:
    """Move every v2-only data tag to its grounded v3 counterpart."""
    out = raw
    counts: dict[str, int] = {}
    for pattern, replacement, _why in TAG_MAP:
        out, n = re.subn(pattern, replacement, out)
        if n:
            counts[pattern] = n
    return out, counts


def derive_tags_variant(decl: str) -> tuple[str, dict[str, int]]:
    """The declaration variant plus the v3 data model."""
    out = decl.replace(TAGS_MODEL_LINE, TAGS_MODEL_V3_LINE, 1)
    if out == decl:
        raise ValueError("the declaration variant does not carry a DATA MODEL line")
    return tag_substitutions(out)


def strip_declarations(raw: str) -> str:
    """Remove the v3 declaration surface, for the 'declarations only' proof.

    The <b:defaultmarkups> block is matched at the start of a line: the theme's own header
    comment *mentions* the tag while explaining it, and a loose pattern happily starts
    matching inside that comment and eats half the file.
    """
    out = raw.replace(TAGS_HEADER_NOTE, "", 1)
    out = re.sub(r"^<b:defaultmarkups>\n.*?^</b:defaultmarkups>\n", "", out, flags=re.S | re.M)
    out = re.sub(r"\s*<!--\s*\n  Layouts v3.*?-->\n", "", out, flags=re.S)
    for pattern in DECL_ATTRS:
        out = re.sub(pattern, "", out)
    return out


def strip_data_tags(raw: str) -> str:
    """Remove every data token (and the literals that replaced some), for structure diffs."""
    out = DATA_TOKEN.sub("", raw)
    for literal in LITERAL_REPLACEMENTS:
        out = out.replace(literal, "")
    return out


def undeclared_changes(decl: str, tags: str) -> list[str]:
    """Lines the tags variant changed that are not a data tag, a documented literal or the
    data-model line. Empty list = every change is accounted for in TAG_MAP."""
    out: list[str] = []
    for line in _changed_lines(decl, tags):
        stripped = line.strip()
        if stripped in (TAGS_MODEL_LINE.strip(), TAGS_MODEL_V3_LINE.strip()):
            continue
        if any(text in line for text in LITERAL_REPLACEMENTS):
            continue
        if "data:" in line or "<b:eval" in line:
            continue
        out.append(stripped)
    return out


def _changed_lines(decl: str, tags: str) -> list[str]:
    import difflib

    produced = (line[2:] for line in difflib.ndiff(decl.splitlines(), tags.splitlines())
                if line.startswith(("+ ", "- ")))
    return list(produced)


def remaining_v2_tags(raw: str) -> list[str]:
    return [pattern for pattern in V2_ONLY_PATTERNS if re.search(pattern, raw)]


def strip_tags_note(raw: str) -> str:
    """Remove the v3-tags provenance note, for the 'data tags only' proof."""
    return raw.replace(TAGS_HEADER_NOTE, "", 1)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def _report(counts: dict[str, int]) -> None:
    for pattern, n in counts.items():
        replacement = next(r for p, r, _ in TAG_MAP if p == pattern)
        print(f"    {n:2d}x  {replacement}")


def main(argv: list[str]) -> int:
    source = _read(SOURCE)
    decl = derive_declaration_variant(source)
    tags, counts = derive_tags_variant(decl)

    if "--stdout" in argv:
        sys.stdout.write(decl)
        return 0

    if "--check" in argv:
        stale = False
        for path, expected in ((DECL_TARGET, decl), (TAGS_TARGET, tags)):
            name = os.path.basename(path)
            try:
                current = _read(path)
            except OSError:
                print(f"STALE: {name} is missing")
                stale = True
                continue
            if current != expected:
                print(f"STALE: {name} differs from a fresh derivation")
                stale = True
        if strip_declarations(decl) != source:
            print("STALE: the declaration variant changes something besides declarations")
            stale = True
        unaccounted = undeclared_changes(decl, tags)
        if unaccounted:
            print("STALE: the tags variant changed lines nobody documented:")
            for line in unaccounted:
                print(f"    {line}")
            stale = True
        left_over = remaining_v2_tags(strip_tags_note(tags))
        if left_over:
            print(f"STALE: the tags variant still carries v2-only data tags: {left_over}")
            stale = True
        if stale:
            return 1
        print("OK: v3-decl == v2-decl + layoutsVersion/defaultmarkups, "
              "v3-tags == v3-decl + grounded data-tag mapping")
        return 0

    _write(DECL_TARGET, decl)
    _write(TAGS_TARGET, tags)
    print(f"wrote {os.path.basename(DECL_TARGET)} ({len(decl)} bytes) "
          f"and {os.path.basename(TAGS_TARGET)} ({len(tags)} bytes) from "
          f"{os.path.basename(SOURCE)}")
    print(f"  <html> gains b:layoutsVersion='{LAYOUTS_VERSION}'")
    print(f"  <b:defaultmarkups> declares {len(DEFAULT_MARKUP_TYPES)} widget-type blocks "
          f"(all empty by design)")
    print("  data tags rewritten in v3-tags (grounded counterparts, with counts):")
    _report(counts)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
