#!/usr/bin/env python3
"""Markdown -> Blogger HTML converter and pre-publish quality gate (JHL-4 §2/§3).

Blogger's editor accepts a limited HTML subset and its API stores the post body as
HTML, so the pipeline converts the repo's markdown masters into clean, whitelisted
HTML instead of hand-pasting rich text. The same module runs the quality gate that
Phase 2 step 7 requires (allowed tags, image rules, search description length,
internal links).

House rules enforced here (see blogger/images/IMAGE-RULES.md):
  * every guide carries at least one <figure> with an <figcaption>
  * every <img> has a non-empty alt, loading="lazy" and decoding="async"
  * body headings shift down one level (# -> h2) because Blogger renders the post
    title as the page <h1>
  * image files are kebab-case .webp and live under assets/images/
  * internal links use [[slug]] or [[slug|anchor text]] and resolve through
    content/link-map.json (Blogger URLs are /YYYY/MM/slug.html, so they cannot be
    guessed at authoring time)

Usage:
    python blogger/md2blogger.py content/posts/example.md               # report + HTML to stdout
    python blogger/md2blogger.py content/posts/example.md --out build/x.html
    python blogger/md2blogger.py content/posts/example.md --emit-payload build/x.json
    python blogger/md2blogger.py content/posts/example.md --json         # machine-readable report
Exit code 1 means the quality gate failed.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import blogger_api as api  # noqa: E402

ALLOWED_TAGS = {
    "p", "br", "hr", "h2", "h3", "h4", "h5", "h6",
    "strong", "em", "b", "i", "code", "pre", "blockquote",
    "ul", "ol", "li", "a", "img", "figure", "figcaption",
    "table", "thead", "tbody", "tr", "th", "td", "small", "span",
}
ALLOWED_ATTRS = {
    "href", "src", "alt", "title", "width", "height", "loading", "decoding",
    "rel", "class", "colspan", "rowspan", "scope", "target", "style",
}
# Responsive image contract: Blogger themes (incl. the live "Simple" skin, ~620px
# post column) do not cap post images, so every <img> carries its own cap.
IMG_STYLE = "display:block;max-width:100%;height:auto;margin:0 auto;padding:0;border:0;box-sizing:border-box"
FIG_STYLE = "margin:1.5em 0;max-width:100%"
IMG_WIDTH = 1200
IMG_MIN_RATIO, IMG_MAX_RATIO = 1.6, 2.0   # 1200x600..1200x750; 1200x630 (1.91:1) recommended


def webp_size(path: str) -> tuple[int, int] | None:
    """(width, height) of a WebP file, stdlib only (VP8 / VP8L / VP8X)."""
    try:
        with open(path, "rb") as fh:
            d = fh.read(40)
    except OSError:
        return None
    if d[:4] != b"RIFF" or d[8:12] != b"WEBP":
        return None
    kind = d[12:16]
    if kind == b"VP8 ":
        return (int.from_bytes(d[26:28], "little") & 0x3FFF, int.from_bytes(d[28:30], "little") & 0x3FFF)
    if kind == b"VP8L":
        b = int.from_bytes(d[21:25], "little")
        return ((b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1)
    if kind == b"VP8X":
        return (int.from_bytes(d[24:27], "little") + 1, int.from_bytes(d[27:30], "little") + 1)
    return None


def _local_image(src: str, cfg: dict) -> str:
    return os.path.join(REPO, (cfg.get("assets") or {}).get("localDir", "assets/images"), src.split("/")[-1])
IMG_EXT_RE = re.compile(r"\.(webp|png|jpe?g|gif|svg|avif)$", re.I)
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.(webp|png|jpe?g|gif|svg|avif)$")
PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+:[^}]+\}\}|\{\{[A-Z_]+\}\}")


class TagAudit(HTMLParser):
    """Collect every tag/attribute used so the whitelist can be enforced."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags: set[str] = set()
        self.attrs: set[str] = set()
        self.imgs: list[dict] = []
        self.figure_depth = 0
        self.figcaption_depth = 0
        self.figures_without_caption: list[int] = []
        self._figure_has_caption = False
        self._figure_index = 0
        self.figure_count = 0

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag)
        d = dict(attrs)
        self.attrs.update(d)
        if tag == "img":
            self.imgs.append(d)
        if tag == "figure":
            self.figure_depth += 1
            self._figure_index += 1
            self.figure_count += 1
            self._figure_has_caption = False
        if tag == "figcaption":
            self.figcaption_depth += 1
            self._figure_has_caption = True

    def handle_endtag(self, tag):
        if tag == "figure":
            if not self._figure_has_caption:
                self.figures_without_caption.append(self._figure_index)
            self.figure_depth = max(0, self.figure_depth - 1)
        if tag == "figcaption":
            self.figcaption_depth = max(0, self.figcaption_depth - 1)


# ------------------------------------------------------------------ frontmatter


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    block = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")
    meta: dict = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("\"'") for v in value[1:-1].split(",")]
            meta[key] = [v for v in items if v]
        elif value.lower() in ("true", "false"):
            meta[key] = value.lower() == "true"
        else:
            meta[key] = value.strip("\"'")
    return meta, body


# ----------------------------------------------------------------------- inline


def _resolve_asset(src: str, cfg: dict, base: str | None) -> tuple[str, str | None]:
    """Return (url_or_placeholder, warning)."""
    if src.startswith(("http://", "https://", "//")):
        return src, None
    public = base or (cfg.get("assets") or {}).get("publicBaseUrl")
    name = src.split("/")[-1]
    if not public:
        return f"{{{{ASSET_BASE}}}}/{name}", (
            f"asset base URL is not configured (config.json -> assets.publicBaseUrl); "
            f"'{name}' left as a placeholder"
        )
    return public.rstrip("/") + "/" + name, None


def inline(text: str, cfg: dict, link_map: dict, warnings: list[str], base: str | None = None) -> str:
    out = html.escape(text, quote=False)

    def _img(match: re.Match) -> str:
        alt, src, caption = match.group(1), match.group(2), match.group(3)
        url, warn = _resolve_asset(src, cfg, base)
        if warn:
            warnings.append(warn)
        cap = f" title='{html.escape(caption, quote=True)}'" if caption else ""
        return (f"<img src=\"{url}\" alt=\"{html.escape(alt, quote=True)}\"{cap} "
                f"style=\"{IMG_STYLE}\" loading=\"lazy\" decoding=\"async\"/>")

    def _wiki(match: re.Match) -> str:
        slug, label = match.group(1).strip(), (match.group(2) or "").strip()
        text_label = html.escape(label or slug)
        if slug in link_map:
            target = link_map[slug]
            if target:
                return f'<a href="{target}">{text_label}</a>'
            # declared in the map but not published yet: no dead link, just text
            warnings.append(f"internal link [[{slug}]] is declared but not published yet — left as plain text")
            return f'<span class="link-pending">{text_label}</span>'
        warnings.append(f"internal link [[{slug}]] is missing from content/link-map.json")
        return f'<span class="link-missing">{text_label}</span>'

    def _link(match: re.Match) -> str:
        label, href = match.group(1), match.group(2)
        rel = ' rel="noopener"' if href.startswith("http") else ""
        return f'<a href="{href}"{rel}>{label}</a>'

    out = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", out)
    out = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+&quot;([^&]*)&quot;|\s+\"([^\"]*)\")?\)", _img, out)
    out = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", _wiki, out)
    out = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _link, out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", out)
    out = re.sub(r"(?<!\w)__([^_]+)__(?!\w)", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"<em>\1</em>", out)
    return out


# ------------------------------------------------------------------------ blocks

HEADING_SHIFT = {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 6}
LIST_RE = re.compile(r"^(\s*)([-*+]|\d+\.)\s+(.*)$")
SEP_RE = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$")
FIGURE_RE = re.compile(r"^!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)\s*$")


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def convert(md: str, cfg: dict, link_map: dict, warnings: list[str], base: str | None = None) -> str:
    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)

    def flush_paragraph(buf: list[str]) -> None:
        if buf:
            out.append("<p>" + inline(" ".join(buf), cfg, link_map, warnings, base) + "</p>")
            buf.clear()

    para: list[str] = []
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # fenced code
        if stripped.startswith("```"):
            flush_paragraph(para)
            lang = stripped[3:].strip()
            i += 1
            code_lines = []
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # closing fence
            cls = f' class="language-{lang}"' if lang else ""
            out.append(f"<pre><code{cls}>{html.escape(chr(10).join(code_lines))}</code></pre>")
            continue

        if not stripped:
            flush_paragraph(para)
            i += 1
            continue

        # editorial notes (HTML comments) are stripped from the published body and
        # surfaced as warnings — the page ships without the reviewer's TODO text
        if stripped.startswith("<!--"):
            note = []
            while i < n:
                note.append(lines[i].strip())
                if "-->" in lines[i]:
                    i += 1
                    break
                i += 1
            text = " ".join(note)[4:]
            text = text[:-3] if text.endswith("-->") else text
            warnings.append("editorial note removed from the body: " + text.strip()[:180])
            continue

        # heading
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_paragraph(para)
            level = HEADING_SHIFT[len(m.group(1))]
            out.append(f"<h{level}>" + inline(m.group(2).strip(), cfg, link_map, warnings, base) + f"</h{level}>")
            i += 1
            continue

        # horizontal rule
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", stripped):
            flush_paragraph(para)
            out.append("<hr/>")
            i += 1
            continue

        # figure (standalone image)
        m = FIGURE_RE.match(stripped)
        if m:
            flush_paragraph(para)
            alt, src, caption = m.group(1), m.group(2), m.group(3)
            url, warn = _resolve_asset(src, cfg, base)
            if warn:
                warnings.append(warn)
            size = webp_size(_local_image(src, cfg))
            if size is None:
                warnings.append(f"could not read dimensions of '{src}' — width/height omitted")
                dims = ""
            else:
                dims = f' width="{size[0]}" height="{size[1]}"'
            out.append(f'<figure style="{FIG_STYLE}">')
            out.append(f'  <img src="{url}" alt="{html.escape(alt, quote=True)}"{dims} '
                       f'style="{IMG_STYLE}" loading="lazy" decoding="async"/>')
            if caption:
                out.append(f"  <figcaption>{inline(caption, cfg, link_map, warnings, base)}</figcaption>")
            else:
                warnings.append(f"figure for '{src}' has no caption (use ![...](src \"caption\"))")
            out.append("</figure>")
            i += 1
            continue

        # blockquote
        if stripped.startswith(">"):
            flush_paragraph(para)
            quoted = []
            while i < n and lines[i].strip().startswith(">"):
                quoted.append(lines[i].strip()[1:].strip())
                i += 1
            text = " ".join(t for t in quoted if t)
            out.append("<blockquote><p>" + inline(text, cfg, link_map, warnings, base) + "</p></blockquote>")
            continue

        # table
        if stripped.startswith("|") and i + 1 < n and SEP_RE.match(lines[i + 1].strip()):
            flush_paragraph(para)
            header = _split_row(lines[i])
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(_split_row(lines[i]))
                i += 1
            out.append("<table><thead><tr>")
            out.extend(f"<th scope=\"col\">{inline(c, cfg, link_map, warnings, base)}</th>" for c in header)
            out.append("</tr></thead><tbody>")
            for row in rows:
                out.append("<tr>")
                out.extend(f"<td>{inline(c, cfg, link_map, warnings, base)}</td>" for c in row)
                out.append("</tr>")
            out.append("</tbody></table>")
            continue

        # lists
        if LIST_RE.match(line):
            flush_paragraph(para)
            m = LIST_RE.match(line)
            ordered = bool(re.match(r"\d+\.", m.group(2)))
            items: list[tuple[int, str, bool]] = []
            while i < n:
                lm = LIST_RE.match(lines[i])
                if lm:
                    indent = len(lm.group(1).replace("\t", "  "))
                    items.append((indent, lm.group(3).strip(), bool(re.match(r"\d+\.", lm.group(2)))))
                    i += 1
                    continue
                nxt = lines[i].strip()
                # lazy continuation: a wrapped line belongs to the item above it
                if nxt and items and not nxt.startswith(("#", "|", ">", "```")):
                    indent, text, is_ordered = items[-1]
                    items[-1] = (indent, f"{text} {nxt}", is_ordered)
                    i += 1
                    continue
                break
            out.append(_render_list(items, cfg, link_map, warnings, base))
            continue

        para.append(stripped)
        i += 1

    flush_paragraph(para)
    return "\n".join(out)


def _render_list(items: list[tuple[int, str, bool]], cfg: dict, link_map: dict,
                 warnings: list[str], base: str | None) -> str:
    """Render a run of list items, nesting one level on indentation."""
    html_out, _ = _build_list(items, 0, cfg, link_map, warnings, base)
    return html_out


def _build_list(items, pos, cfg, link_map, warnings, base, base_indent=None):
    """Return (html, next_index). Items more indented than the current level nest."""
    if base_indent is None:
        base_indent = items[pos][0]
    ordered = items[pos][2]
    tag = "ol" if ordered else "ul"
    parts = [f"<{tag}>"]
    while pos < len(items):
        indent, text, _is_ordered = items[pos]
        if indent < base_indent:
            break
        if indent > base_indent:
            nested, pos = _build_list(items, pos, cfg, link_map, warnings, base, indent)
            # a nested list must live inside the previous <li>
            if parts[-1].endswith("</li>"):
                parts[-1] = parts[-1][: -len("</li>")] + nested + "</li>"
            else:
                parts.append(nested)
            continue
        parts.append("<li>" + inline(text, cfg, link_map, warnings, base) + "</li>")
        pos += 1
    parts.append(f"</{tag}>")
    return "".join(parts), pos


# -------------------------------------------------------------------------- gate


def quality_gate(html_body: str, meta: dict, audit: TagAudit, cfg: dict,
                 errors: list[str], warnings: list[str]) -> None:
    unknown_tags = sorted(audit.tags - ALLOWED_TAGS)
    if unknown_tags:
        errors.append(f"tags outside the Blogger whitelist: {unknown_tags}")
    unknown_attrs = sorted({a for a in audit.attrs if a not in ALLOWED_ATTRS and a != "class"})
    if unknown_attrs:
        warnings.append(f"attributes not in the whitelist: {unknown_attrs}")

    if not html_body.strip():
        errors.append("post body is empty")

    if not audit.imgs:
        errors.append("no image in the guide — every guide needs at least one visual")
    if audit.figures_without_caption:
        errors.append(f"{len(audit.figures_without_caption)} <figure> block(s) without <figcaption>")
    for img in audit.imgs:
        if not (img.get("alt") or "").strip():
            errors.append(f"image without alt text: {img.get('src')}")
        if "max-width:100%" not in (img.get("style") or "").replace(" ", ""):
            errors.append(f"image not capped to the column (needs style max-width:100%;height:auto): {img.get('src')}")
        size = webp_size(_local_image(str(img.get("src", "")), cfg))
        if size:
            w, h = size
            if w != IMG_WIDTH:
                errors.append(f"image is {w}px wide, house size is {IMG_WIDTH}px: {img.get('src')}")
            if not (IMG_MIN_RATIO <= w / h <= IMG_MAX_RATIO):
                errors.append(f"image aspect {w}x{h} ({w/h:.2f}:1) outside {IMG_MIN_RATIO}-{IMG_MAX_RATIO}:1: {img.get('src')}")
            if img.get("width") and str(img.get("width")) != str(w):
                errors.append(f"width attr {img.get('width')} != file width {w}: {img.get('src')}")
        if img.get("loading") != "lazy":
            warnings.append(f"image missing loading=\"lazy\": {img.get('src')}")
        name = os.path.basename(str(img.get("src", "")))
        if name and IMG_EXT_RE.search(name) and not KEBAB_RE.match(name):
            warnings.append(f"image file is not kebab-case .webp: {name}")

    description = (meta.get("description") or "").strip()
    limit = cfg["publishing"]["searchDescriptionMaxLength"]
    if not description:
        errors.append("frontmatter is missing 'description' (Blogger search description)")
    elif len(description) > limit:
        errors.append(f"description is {len(description)} chars — Blogger's search description limit is {limit}")

    labels = meta.get("labels") or []
    known = set((cfg.get("labels") or {}).values())
    unknown_labels = [lb for lb in labels if lb not in known]
    if unknown_labels:
        errors.append(f"labels outside the Phase 0 category model: {unknown_labels}")
    if not labels:
        errors.append("frontmatter is missing 'labels' (Blogger category)")

    title = (meta.get("title") or "").strip()
    if not title:
        errors.append("frontmatter is missing 'title'")
    elif len(title) > 65:
        warnings.append(f"title is {len(title)} chars — keep titles under ~65 for full SERP display")

    # Site host(s) come from config.json — never hard-coded, so the blogspot -> custom
    # domain switch (or a rename) cannot silently break this check.
    site_hosts = {urlsplit(url).netloc for url in (
        (cfg.get("blog") or {}).get("customDomainUrl"),
        (cfg.get("blog") or {}).get("blogspotUrl"),
    ) if url}
    hrefs = re.findall(r'href="([^"]+)"', html_body)
    internal = [h for h in hrefs if h.startswith("/") or urlsplit(h).netloc in site_hosts]
    if len(internal) < 2:
        warnings.append(f"only {len(internal)} internal link(s) — target 2+ internal links per guide")
    if "link-missing" in html_body:
        errors.append("unresolved [[slug]] internal link(s) — add them to content/link-map.json")


# --------------------------------------------------------------------------- api


def build_post_payload(md_path: str, cfg: dict, base: str | None = None,
                       link_map_path: str | None = None) -> dict:
    """Convert one markdown master into a Blogger post payload + gate report."""
    with open(md_path, encoding="utf-8") as fh:
        raw = fh.read()
    meta, body_md = parse_frontmatter(raw)
    slug = meta.get("slug") or os.path.splitext(os.path.basename(md_path))[0]

    link_map_path = link_map_path or os.path.join(REPO, cfg["links"]["mapFile"])
    link_map: dict = {}
    if os.path.isfile(link_map_path):
        with open(link_map_path, encoding="utf-8") as fh:
            link_map = json.load(fh)

    warnings: list[str] = []
    html_body = convert(body_md, cfg, link_map, warnings, base)
    audit = TagAudit()
    audit.feed(html_body)
    errors: list[str] = []
    quality_gate(html_body, meta, audit, cfg, errors, warnings)

    unresolved = PLACEHOLDER_RE.findall(html_body)
    if unresolved:
        errors.append(f"unresolved placeholders in the body: {sorted(set(unresolved))}")

    payload = {
        "title": meta.get("title", ""),
        "content": html_body,
        "labels": meta.get("labels", []),
    }
    try:
        source = os.path.relpath(md_path, REPO).replace("\\", "/")
    except ValueError:
        # master outside the repo (e.g. on another drive) — keep the path readable
        source = os.path.abspath(md_path).replace("\\", "/")
    return {
        "source": source,
        "slug": slug,
        "status": meta.get("status", "draft"),
        "search_description": meta.get("description", ""),
        "search_description_note": (
            "Blogger API v3 has no field for the search description (only the editor UI "
            "writes it). The theme falls back to the post snippet, so this text is kept "
            "here for the reviewer to paste into the editor if a custom one is wanted."
        ),
        "payload": payload,
        "errors": errors,
        "warnings": warnings,
        "image_count": len(audit.imgs),
        "figure_count": audit.figure_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Markdown -> Blogger HTML + quality gate")
    parser.add_argument("markdown", help="path to the markdown master (content/posts/*.md)")
    parser.add_argument("--out", help="write the converted HTML here")
    parser.add_argument("--emit-payload", help="write the Blogger post payload JSON here")
    parser.add_argument("--json", action="store_true", help="print the full report as JSON")
    parser.add_argument("--assets-base", help="override assets.publicBaseUrl for this run")
    parser.add_argument("--link-map", help="path to the slug -> Blogger URL map")
    args = parser.parse_args()

    cfg = api.load_config()
    report = build_post_payload(args.markdown, cfg, args.assets_base, args.link_map)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report["payload"]["content"])
        print(f"HTML written: {args.out}")
    if args.emit_payload:
        with open(args.emit_payload, "w", encoding="utf-8") as fh:
            json.dump(report["payload"], fh, ensure_ascii=False, indent=2)
        print(f"Payload written: {args.emit_payload}")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"source: {report['source']}")
        print(f"title:  {report['payload']['title']} ({len(report['payload']['title'])} chars)")
        print(f"labels: {', '.join(report['payload']['labels']) or '(none)'}")
        print(f"body:   {len(report['payload']['content'])} chars, {report['image_count']} image(s)")
        print(f"search description: {len(report['search_description'])} chars")
        for w in report["warnings"]:
            print(f"  WARN  {w}")
        for e in report["errors"]:
            print(f"  ERROR {e}")
        if not args.out:
            print("\n---- converted HTML ----")
            print(report["payload"]["content"])
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
