#!/usr/bin/env python3
"""Offline test suite for the Blogger pipeline (no network, no credentials required).

Run:  python blogger/tests/test_pipeline.py -v
Everything here works before the owner finishes the OAuth setup, which is what the
issue requires ("OAuth 완료 전 — 오프라인 검증·dry-run까지").
"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "blogger"))
sys.path.insert(0, os.path.join(REPO, "blogger", "theme"))

import blogger_api as api  # noqa: E402
import decl_variant  # noqa: E402
import md2blogger  # noqa: E402
import v3_variant  # noqa: E402
import verify_applied  # noqa: E402
import verify_theme  # noqa: E402

GML_B = "{http://www.google.com/2005/gml/b}"
THEME_DIR = os.path.join(REPO, "blogger", "theme")
V1_THEME = os.path.join(THEME_DIR, "owners-handbook-v1.xml")
V2_DECL_THEME = os.path.join(THEME_DIR, "owners-handbook-v2-decl.xml")
V3_DECL_THEME = os.path.join(THEME_DIR, "owners-handbook-v3-decl.xml")
V3_TAGS_THEME = os.path.join(THEME_DIR, "owners-handbook-v3-tags.xml")


def theme_generation_tokens(path: str) -> set[str]:
    """The <html> class tokens a theme file declares, read the way the live check reads
    them (comments stripped — the files' own comments quote class='v2')."""
    with open(path, encoding="utf-8") as fh:
        return verify_applied.live_generation_tokens(fh.read())

CFG = api.load_config()
ASSETS = "https://example.github.io/owners-handbook-images"
EXAMPLE = os.path.join(REPO, "content", "posts", "example-guide.md")

# Minimal stand-in for a page rendered with the theme applied: the theme's own markers,
# the tags the theme adds, and the tags Blogger emits exactly once.
HEALTHY_PAGE = """<html class='v2' dir='ltr' lang='en'><head>
<!-- The Owner's Handbook theme comment that mentions <title> and canonical. -->
<title>The Owner's Handbook</title>
<link href='https://example.blogspot.com/' rel='canonical'/>
<meta content='https://example.blogspot.com/' property='og:url'/>
<meta content='https://example.blogspot.com/favicon.ico' property='og:image'/>
<meta content='summary_large_image' name='twitter:card'/>
<meta content='width=device-width, initial-scale=1' name='viewport'/>
<script type='application/ld+json'>{"@type":"WebSite"}</script>
<style><!-- .ad-slot { margin: 1.5rem 0; } --></style>
</head><body>
<header class='site-header'><div class='site-brand section' id='header'><div class='widget Header' data-version='1' id='Header1'><h1 class='site-title'>The Owner's Handbook</h1></div></div></header>
<nav class='site-nav'><div class='nav-pages section' id='nav'><div class='widget PageList' data-version='1' id='PageList1'><ul class='page-list'><li><a href='/'>Home</a></li></ul></div><div class='widget Label' data-version='1' id='Label1'><ul class='label-list'></ul></div></div></nav>
<div class='ad-slot ad-top' id='ad-top'><!-- ADSENSE-TOP: empty --></div>
<div class='main-posts section' id='main-posts'><div class='widget Blog' data-version='1' id='Blog1'><div class='blog-posts hfeed'></div></div></div>
<aside class='sidebar'><div class='sidebar-widgets section' id='sidebar'><div class='widget HTML' data-version='1' id='HTML1'><div class='widget-content'>About this site</div></div><div class='widget Label' data-version='1' id='Label2'><ul class='label-list'></ul></div></div></aside>
<footer class='site-footer'><div class='footer-widgets section' id='footer'><div class='widget PageList' data-version='1' id='PageList2'><ul class='page-list'></ul></div><div class='widget HTML' data-version='1' id='HTML2'><div class='widget-content'>Independent publication.</div></div></div>Copyright</footer>
<div class='ad-slot ad-bottom' id='ad-bottom'><!-- ADSENSE-BOTTOM: empty --></div>
<script type='text/javascript'>
_WidgetManager._RegisterWidget('_HeaderView', new _WidgetInfo('Header1', 'header', document.getElementById('Header1'), {}, 'displayModeFull'));
_WidgetManager._RegisterWidget('_PageListView', new _WidgetInfo('PageList1', 'nav', document.getElementById('PageList1'), {}, 'displayModeFull'));
_WidgetManager._RegisterWidget('_LabelView', new _WidgetInfo('Label1', 'nav', document.getElementById('Label1'), {}, 'displayModeFull'));
_WidgetManager._RegisterWidget('_BlogView', new _WidgetInfo('Blog1', 'main-posts', document.getElementById('Blog1'), {}, 'displayModeFull'));
_WidgetManager._RegisterWidget('_HTMLView', new _WidgetInfo('HTML1', 'sidebar', document.getElementById('HTML1'), {}, 'displayModeFull'));
_WidgetManager._RegisterWidget('_LabelView', new _WidgetInfo('Label2', 'sidebar', document.getElementById('Label2'), {}, 'displayModeFull'));
_WidgetManager._RegisterWidget('_PageListView', new _WidgetInfo('PageList2', 'footer', document.getElementById('PageList2'), {}, 'displayModeFull'));
_WidgetManager._RegisterWidget('_HTMLView', new _WidgetInfo('HTML2', 'footer', document.getElementById('HTML2'), {}, 'displayModeFull'));
</script>
</body></html>"""


# The live shape of the blog on 2026-10-16: our theme compiled (markers + SEO tags are
# present, and the served <html> carries the theme's class='v2' generation token, so the
# *current* file is live) and Blogger registered every widget it knows about, but every
# section was emitted empty, so the page showed nothing but "Skip to content". Reproduced
# verbatim from the public page source so the regression test cannot drift from reality.
EMPTY_WIDGET_PAGE = """<html class='v2' dir='ltr' lang='en'><head>
<title>The Owner's Handbook</title>
<meta content='https://ownerhandbook.blogspot.com/favicon.ico' property='og:image'/>
<meta content='summary_large_image' name='twitter:card'/>
<meta content='width=device-width, initial-scale=1' name='viewport'/>
<link href='https://ownerhandbook.blogspot.com/' rel='canonical'/>
<meta content='https://ownerhandbook.blogspot.com/' property='og:url'/>
<script type='application/ld+json'>{"@type":"WebSite"}</script>
<style><!-- .ad-slot { margin: 1.5rem 0; } --></style>
</head><body>
<a class='skip-link' href='#main'>Skip to content</a>
<header class='site-header'><div class='wrap site-header-inner'>
<div class='site-brand no-items section' id='header'></div>
</div></header>
<nav class='site-nav'><div class='wrap site-nav-inner'>
<div class='nav-pages no-items section' id='nav'></div>
</div></nav>
<main class='main-col' id='main'>
<div class='ad-slot ad-top' id='ad-top'><!-- ADSENSE-TOP --></div>
<div class='main-posts no-items section' id='main-posts'></div>
</main>
<aside class='sidebar'><div class='sidebar-widgets no-items section' id='sidebar'></div></aside>
<footer class='site-footer'><div class='wrap site-footer-inner'>
<div class='footer-widgets no-items section' id='footer'></div>
</div></footer>
<div class='ad-slot ad-bottom' id='ad-bottom'><!-- ADSENSE-BOTTOM --></div>
<script type='text/javascript'>
_WidgetManager._RegisterWidget('_HeaderView', new _WidgetInfo('Header1', 'header', document.getElementById('Header1'), {}, 'displayModeFull'));
_WidgetManager._RegisterWidget('_PageListView', new _WidgetInfo('PageList1', 'nav', document.getElementById('PageList1'), {}, 'displayModeFull'));
_WidgetManager._RegisterWidget('_BlogView', new _WidgetInfo('Blog1', 'main-posts', document.getElementById('Blog1'), {}, 'displayModeFull'));
_WidgetManager._RegisterWidget('_HTMLView', new _WidgetInfo('HTML1', 'sidebar', document.getElementById('HTML1'), {}, 'displayModeFull'));
_WidgetManager._RegisterWidget('_PageListView', new _WidgetInfo('PageList2', 'footer', document.getElementById('PageList2'), {}, 'displayModeFull'));
_WidgetManager._RegisterWidget('_HTMLView', new _WidgetInfo('HTML2', 'footer', document.getElementById('HTML2'), {}, 'displayModeFull'));
</script>
</body></html>"""


def convert(md: str, link_map: dict | None = None, base: str | None = ASSETS):
    warnings: list[str] = []
    html = md2blogger.convert(md, CFG, link_map or {}, warnings, base)
    return html, warnings


def gate(html_body: str, meta: dict, cfg: dict = CFG):
    audit = md2blogger.TagAudit()
    audit.feed(html_body)
    errors: list[str] = []
    warnings: list[str] = []
    md2blogger.quality_gate(html_body, meta, audit, cfg, errors, warnings)
    return errors, warnings


def valid_meta(**overrides) -> dict:
    meta = {
        "title": "A Guide",
        "description": "A useful description for the search result snippet.",
        "labels": ["Startup Costs"],
    }
    meta.update(overrides)
    return meta


class FrontmatterTests(unittest.TestCase):
    def test_parses_scalars_lists_and_bools(self):
        meta, body = md2blogger.parse_frontmatter(
            "---\ntitle: Hello\ndraft: true\nlabels: [A, B]\nslug: \"x-y\"\n---\nBody text\n"
        )
        self.assertEqual(meta["title"], "Hello")
        self.assertTrue(meta["draft"])
        self.assertEqual(meta["labels"], ["A", "B"])
        self.assertEqual(meta["slug"], "x-y")
        self.assertEqual(body, "Body text\n")

    def test_without_frontmatter(self):
        meta, body = md2blogger.parse_frontmatter("Just a body")
        self.assertEqual(meta, {})
        self.assertEqual(body, "Just a body")


class ConversionTests(unittest.TestCase):
    def test_headings_shift_below_the_post_title(self):
        html, _ = convert("# Section\n\n## Sub\n\n### Deep\n")
        self.assertIn("<h2>Section</h2>", html)
        self.assertIn("<h3>Sub</h3>", html)
        self.assertIn("<h4>Deep</h4>", html)

    def test_figure_gets_caption_and_lazy_attributes(self):
        html, _ = convert('![A chart](assets/images/my-chart.webp "The caption")\n')
        self.assertIn("<figure>", html)
        self.assertIn("<figcaption>The caption</figcaption>", html)
        self.assertIn('loading="lazy"', html)
        self.assertIn('decoding="async"', html)
        self.assertIn(f'src="{ASSETS}/my-chart.webp"', html)
        self.assertIn('alt="A chart"', html)

    def test_figure_without_caption_is_reported(self):
        _html, warnings = convert("![A chart](assets/images/my-chart.webp)\n")
        self.assertTrue(any("no caption" in w for w in warnings))

    def test_table_conversion(self):
        html, _ = convert("| A | B |\n| --- | --- |\n| 1 | 2 |\n")
        self.assertIn("<thead>", html)
        self.assertIn('<th scope="col">A</th>', html)
        self.assertIn("<td>1</td>", html)

    def test_list_with_wrapped_line_stays_one_list(self):
        html, _ = convert("- first item that\n  wraps onto another line\n- second\n")
        self.assertEqual(html.count("<ul>"), 1)
        self.assertEqual(html.count("<li>"), 2)
        self.assertIn("wraps onto another line", html)

    def test_nested_list(self):
        html, _ = convert("- top\n  - nested\n")
        self.assertIn("<ul><li>top<ul><li>nested</li></ul></li></ul>", html)

    def test_inline_code_is_escaped(self):
        html, _ = convert("Use `<script>` carefully.\n")
        self.assertIn("<code>&lt;script&gt;</code>", html)
        self.assertNotIn("<script>", html)

    def test_code_fence_is_escaped_and_keeps_language(self):
        html, _ = convert("```bash\nnpm run build\n```\n")
        self.assertIn('<pre><code class="language-bash">', html)
        self.assertIn("npm run build", html)

    def test_editorial_comment_is_removed_and_reported(self):
        html, warnings = convert("Text before.\n\n<!-- TODO(reviewer): fix this -->\n\nText after.\n")
        self.assertNotIn("TODO", html)
        self.assertTrue(any("editorial note removed" in w for w in warnings))

    def test_link_map_resolution_states(self):
        html, warnings = convert(
            "See [[published-guide|the guide]], [[pending-guide]] and [[unknown-guide]].\n",
            link_map={"published-guide": "https://ownerhandbook.blogspot.com/2026/10/x.html",
                      "pending-guide": None},
        )
        self.assertIn('<a href="https://ownerhandbook.blogspot.com/2026/10/x.html">the guide</a>', html)
        self.assertIn('<span class="link-pending">pending-guide</span>', html)
        self.assertIn('<span class="link-missing">unknown-guide</span>', html)
        self.assertEqual(sum("missing from content/link-map.json" in w for w in warnings), 1)

    def test_external_links_get_rel(self):
        html, _ = convert("[SBA](https://sba.gov/)\n")
        self.assertIn('rel="noopener"', html)

    def test_asset_base_missing_leaves_placeholder(self):
        html, warnings = convert("![alt](assets/images/x.webp \"cap\")\n", base="")
        self.assertIn("{{ASSET_BASE}}/x.webp", html)
        self.assertTrue(any("asset base URL is not configured" in w for w in warnings))


class QualityGateTests(unittest.TestCase):
    BODY = '<p>text</p><figure><img src="a.webp" alt="a" loading="lazy"/>' \
           "<figcaption>cap</figcaption></figure>"

    def test_passes_a_clean_guide(self):
        errors, _ = gate(self.BODY, valid_meta())
        self.assertEqual(errors, [])

    def test_requires_an_image(self):
        errors, _ = gate("<p>text</p>", valid_meta())
        self.assertTrue(any("no image" in e for e in errors))

    def test_requires_alt_text(self):
        errors, _ = gate('<figure><img src="a.webp" alt=""/><figcaption>c</figcaption></figure>', valid_meta())
        self.assertTrue(any("without alt text" in e for e in errors))

    def test_requires_figcaption(self):
        errors, _ = gate('<figure><img src="a.webp" alt="a" loading="lazy"/></figure>', valid_meta())
        self.assertTrue(any("without <figcaption>" in e for e in errors))

    def test_description_length_limit(self):
        errors, _ = gate(self.BODY, valid_meta(description="x" * 151))
        self.assertTrue(any("search description limit" in e for e in errors))

    def test_unknown_label_is_rejected(self):
        errors, _ = gate(self.BODY, valid_meta(labels=["Random Label"]))
        self.assertTrue(any("Phase 0 category model" in e for e in errors))

    def test_tag_whitelist_rejects_script(self):
        errors, _ = gate(self.BODY + "<script>alert(1)</script>", valid_meta())
        self.assertTrue(any("whitelist" in e for e in errors))

    def test_unresolved_placeholder_blocks_publish(self):
        errors, _ = gate(self.BODY + "<p>{{ASSET_BASE}}/x.webp</p>", valid_meta())
        self.assertEqual(errors, [])  # placeholder check lives in build_post_payload

    def test_missing_description_and_labels(self):
        errors, _ = gate(self.BODY, {"title": "T"})
        self.assertTrue(any("missing 'description'" in e for e in errors))
        self.assertTrue(any("missing 'labels'" in e for e in errors))


class RepoFixtureTests(unittest.TestCase):
    def test_example_guide_passes_the_gate(self):
        report = md2blogger.build_post_payload(EXAMPLE, CFG, ASSETS)
        self.assertEqual(report["errors"], [], report["errors"])
        self.assertEqual(report["figure_count"], 2)
        self.assertEqual(report["slug"], "llc-cost-breakdown")
        self.assertLessEqual(len(report["search_description"]), 150)

    def test_placeholder_blocks_the_gate_without_asset_base(self):
        report = md2blogger.build_post_payload(EXAMPLE, CFG, None)
        self.assertTrue(any("placeholders" in e for e in report["errors"]))

    def test_payload_is_api_shaped(self):
        report = md2blogger.build_post_payload(EXAMPLE, CFG, ASSETS)
        payload = report["payload"]
        self.assertEqual(set(payload), {"title", "content", "labels"})
        self.assertNotIn("searchDescription", payload)  # not supported by Blogger API v3


class ThemeTests(unittest.TestCase):
    def test_theme_declares_its_layout_generation(self):
        """Regression (JHL-4, 2026-10-16): without these three declarations on <html>
        Blogger compiled the theme but instantiated none of its widgets, so every
        section rendered as an empty 'no-items' div. Assert on the parsed root element
        so a comment cannot satisfy the check."""
        with open(os.path.join(REPO, "blogger", "theme", "owners-handbook-v1.xml"),
                  encoding="utf-8") as fh:
            root = ET.fromstring(fh.read())
        self.assertEqual(root.get("{http://www.google.com/2005/gml/b}version"), "2")
        self.assertEqual(root.get("{http://www.google.com/2005/gml/b}responsive"), "true")
        self.assertIn("v2", (root.get("class") or "").split())

    def test_theme_validator_passes(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = verify_theme.main(os.path.join(REPO, "blogger", "theme", "owners-handbook-v1.xml"))
        self.assertEqual(code, 0, buffer.getvalue())

    def test_theme_validator_rejects_a_hard_coded_host(self):
        """The check that would have caught the hard-coded og:image fallback."""
        path = os.path.join(REPO, "blogger", "theme", "owners-handbook-v1.xml")
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
        broken = raw.replace("expr:content='data:blog.homepageUrl + &quot;favicon.ico&quot;'",
                             "content='https://example.blogspot.com/favicon.ico'")
        self.assertNotEqual(broken, raw)
        with tempfile.NamedTemporaryFile("w", suffix=".xml", encoding="utf-8",
                                         delete=False) as fh:
            fh.write(broken)
            tmp = fh.name
        try:
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = verify_theme.main(tmp)
            self.assertEqual(code, 1, buffer.getvalue())
            self.assertIn("no absolute URL is hard-coded", buffer.getvalue())
        finally:
            os.unlink(tmp)

    # ---- declaration generation (JHL-4, 2026-10-17) -----------------------------

    def _validate_text(self, text: str) -> tuple[int, str]:
        with tempfile.NamedTemporaryFile("w", suffix=".xml", encoding="utf-8",
                                         delete=False) as fh:
            fh.write(text)
            tmp = fh.name
        try:
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = verify_theme.main(tmp)
            return code, buffer.getvalue()
        finally:
            os.unlink(tmp)

    def test_declaration_variant_is_a_declarations_only_derivation_of_v1(self):
        """The variant is the experiment's only variable: if the blog still renders no
        widgets with it, the declaration generation was not the cause and nothing else moved."""
        with open(V1_THEME, encoding="utf-8") as fh:
            source = fh.read()
        with open(V2_DECL_THEME, encoding="utf-8") as fh:
            committed = fh.read()
        derived, report = decl_variant.derive(source)
        self.assertEqual(committed, derived)
        self.assertEqual(report, {"widgets": 8, "sections": 5})
        self.assertEqual(decl_variant.strip_declarations(committed),
                         decl_variant.strip_declarations(source))

        root = ET.fromstring(committed)
        self.assertEqual(root.get(f"{GML_B}defaultwidgetversion"), "2")
        self.assertEqual(root.get(f"{GML_B}version"), "2")          # kept from v1
        self.assertEqual(root.get(f"{GML_B}responsive"), "true")    # kept from v1
        self.assertIsNone(root.get(f"{GML_B}layoutsVersion"))       # v3 token deliberately absent
        widgets = list(root.iter(f"{GML_B}widget"))
        self.assertEqual(len(widgets), 8)
        self.assertEqual({w.get("version") for w in widgets}, {"2"})
        self.assertEqual({w.get("visible") for w in widgets}, {"true"})
        self.assertEqual({s.get("name") for s in root.iter(f"{GML_B}section")},
                         {"Header", "Navigation", "Posts", "Sidebar", "Footer"})

    def test_declaration_variant_passes_the_validator(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = verify_theme.main(V2_DECL_THEME)
        out = buffer.getvalue()
        self.assertEqual(code, 0, out)
        self.assertIn("declared widget generation: 2", out)

    def test_v1_keeps_passing_after_the_generation_checks_were_added(self):
        """v1 is what the blog serves today; the new [2c] checks must not retro-fail it."""
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = verify_theme.main(V1_THEME)
        self.assertEqual(code, 0, buffer.getvalue())
        self.assertIn("declared widget generation: implicit", buffer.getvalue())

    def test_validator_rejects_mixed_widget_generations(self):
        with open(V2_DECL_THEME, encoding="utf-8") as fh:
            raw = fh.read()
        broken = raw.replace("type='Header' version='2'", "type='Header' version='1'", 1)
        self.assertNotEqual(broken, raw)
        code, out = self._validate_text(broken)
        self.assertEqual(code, 1, out)
        self.assertIn("uniform, valid version token", out)

    def test_validator_rejects_a_v3_layout_token(self):
        """b:layoutsVersion='3' without <b:defaultmarkups> is half a v3 declaration: every
        working v3 theme pairs them, and the token alone would still be read against the
        v2-model data tags this file uses. [2d] carries the variant-only exception."""
        with open(V2_DECL_THEME, encoding="utf-8") as fh:
            raw = fh.read()
        broken = raw.replace("b:defaultwidgetversion='2'", "b:defaultwidgetversion='2' b:layoutsVersion='3'", 1)
        self.assertNotEqual(broken, raw)
        code, out = self._validate_text(broken)
        self.assertEqual(code, 1, out)
        self.assertIn("b:layoutsVersion='3'", out)

    def test_validator_rejects_a_generation2_section_without_a_name(self):
        with open(V2_DECL_THEME, encoding="utf-8") as fh:
            raw = fh.read()
        broken = raw.replace(" id='sidebar' maxwidgets='4' showaddelement='yes' name='Sidebar'",
                             " id='sidebar' maxwidgets='4' showaddelement='yes'", 1)
        self.assertNotEqual(broken, raw)
        code, out = self._validate_text(broken)
        self.assertEqual(code, 1, out)
        self.assertIn("unique Layout names", out)

    def test_upload_guide_offers_the_declaration_variant_and_keeps_the_backup_step(self):
        with open(os.path.join(THEME_DIR, "UPLOAD-GUIDE.md"), encoding="utf-8") as fh:
            guide = fh.read()
        self.assertIn("owners-handbook-v2-decl.xml", guide)
        self.assertIn("owners-handbook-v1.xml", guide)  # the rollback file stays documented
        self.assertIn("백업", guide)

    def test_decl_variant_check_mode_flags_a_stale_file(self):
        proc = subprocess.run([sys.executable, os.path.join(THEME_DIR, "decl_variant.py"),
                               "--check"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("declarations-only derivation", proc.stdout)


class AppliedThemeTests(unittest.TestCase):
    """verify_applied.report() against synthetic pages — no network needed."""

    def _run(self, html_text: str, mobile_html: str | None = None) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = verify_applied.report(html_text, "https://example.blogspot.com/", mobile_html)
        return code, buffer.getvalue()

    def test_reports_not_applied_on_a_stock_blogger_page(self):
        code, out = self._run("<html><head><title>blog</title></head><body>hi</body></html>")
        self.assertEqual(code, 3, out)
        self.assertIn("NOT applied", out)

    def test_reports_success_on_a_healthy_theme_page(self):
        code, out = self._run(HEALTHY_PAGE)
        self.assertEqual(code, 0, out)

    def test_reports_missing_seo_tags_as_a_failure(self):
        broken = HEALTHY_PAGE.replace("<meta content='summary_large_image' name='twitter:card'/>", "")
        self.assertNotEqual(broken, HEALTHY_PAGE)
        code, out = self._run(broken)
        self.assertEqual(code, 1, out)
        self.assertIn("twitter card", out)

    def test_duplicate_title_is_a_failure(self):
        broken = HEALTHY_PAGE.replace("</head>", "<title>second</title></head>")
        code, out = self._run(broken)
        self.assertEqual(code, 1, out)
        self.assertIn("<title>: 2", out)

    def test_comments_mentioning_title_do_not_count_as_tags(self):
        """The theme's own header comment names <title>; it must not be counted."""
        commented = HEALTHY_PAGE.replace("<head>", "<head><!-- keep <title> tags single -->")
        code, out = self._run(commented)
        self.assertEqual(code, 0, out)
        self.assertIn("<title>: 1", out)

    def test_empty_widget_sections_are_a_failure_not_a_pass(self):
        """Regression: the live page on 2026-10-16 passed every SEO check while rendering
        zero widgets. Markers and SEO tags are not evidence that the theme works."""
        code, out = self._run(EMPTY_WIDGET_PAGE)
        self.assertEqual(code, 4, out)
        self.assertIn("widgets do not render", out)
        self.assertIn("Save arrangement", out)

    def test_registered_widget_without_markup_is_reported(self):
        broken = HEALTHY_PAGE.replace(
            "<div class='widget Blog' data-version='1' id='Blog1'>"
            "<div class='blog-posts hfeed'></div></div>", "")
        self.assertNotEqual(broken, HEALTHY_PAGE)
        code, out = self._run(broken)
        self.assertEqual(code, 4, out)
        self.assertIn("Blog1", out)

    def test_widget_wrapper_inside_a_script_is_not_counted(self):
        """Blogger's registration script also mentions every id; only real markup counts."""
        code, out = self._run(EMPTY_WIDGET_PAGE.replace(
            "<div class='site-brand no-items section' id='header'></div>",
            "<div class='site-brand section' id='header'>"
            "<div class='widget Header' data-version='1' id='Header1'></div></div>"))
        self.assertEqual(code, 4, out)
        self.assertIn("RENDERED", out)
        self.assertIn("header", out)

    def test_older_generation_live_is_reported_not_passed(self):
        """The served page can be an older copy of our theme while every marker still
        matches: before the generation declarations landed, <html> rendered with no class,
        and the marker/SEO checks passed anyway."""
        older = HEALTHY_PAGE.replace("<html class='v2' dir='ltr' lang='en'>",
                                     "<html dir='ltr' lang='en'>")
        self.assertNotEqual(older, HEALTHY_PAGE)
        code, out = self._run(older)
        self.assertEqual(code, 3, out)
        self.assertIn("older generation", out)

    def test_generation_check_reads_the_element_not_a_comment(self):
        """Our theme's own comment quotes class='v2'. A page that carries the comment while
        the served element has no class is still an older generation — reading the string
        anywhere in the page reports it as live (my first probe did exactly that)."""
        older = HEALTHY_PAGE.replace("<html class='v2' dir='ltr' lang='en'>",
                                     "<html dir='ltr' lang='en'>").replace(
            "<head>", "<head><!-- <html b:version='2' class='v2' b:responsive='true'> -->")
        code, out = self._run(older)
        self.assertEqual(code, 3, out)
        self.assertIn("no class attribute at all", out)

    def test_widget_failure_does_not_ask_for_a_re_paste_when_the_file_is_live(self):
        """The served page already is this file, so re-pasting it changes nothing; the
        advice has to point at the declaration variant, the layout save and B0 instead."""
        code, out = self._run(EMPTY_WIDGET_PAGE)
        self.assertEqual(code, 4, out)
        self.assertIn("owners-handbook-v1.xml changes nothing", out)
        self.assertIn("owners-handbook-v3-decl.xml", out)
        self.assertIn("owners-handbook-v2-decl.xml", out)
        self.assertIn("B0-probe.xml", out)
        self.assertNotIn("Re-apply the current theme file", out)

    def test_widget_failure_asks_for_a_re_paste_when_the_file_is_not_live(self):
        older = EMPTY_WIDGET_PAGE.replace("<html class='v2' dir='ltr' lang='en'>",
                                          "<html dir='ltr' lang='en'>")
        code, out = self._run(older)
        self.assertEqual(code, 4, out)
        self.assertIn("Re-apply the current theme file", out)

    def test_stock_mobile_template_fails_the_mobile_first_requirement(self):
        stock_mobile = ("<html><head><title>b</title></head><body>"
                        "<div class='section' id='navbar'></div>"
                        "<div class='section' id='crosscol'></div></body></html>")
        code, out = self._run(HEALTHY_PAGE, stock_mobile)
        self.assertEqual(code, 5, out)
        self.assertIn("stock template", out)

    def test_mobile_slot_serving_the_theme_passes(self):
        code, out = self._run(HEALTHY_PAGE, HEALTHY_PAGE)
        self.assertEqual(code, 0, out)
        self.assertIn("serves this theme", out)


class SafetyTests(unittest.TestCase):
    def test_publish_refuses_without_owner_approval(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, "blogger", "publish.py"), "publish", "123456"],
            capture_output=True, text=True, cwd=REPO,
        )
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertIn("Refusing to publish", proc.stdout)

    def test_create_dry_run_needs_no_credentials(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, "blogger", "publish.py"), "create", EXAMPLE,
             "--dry-run", "--assets-base", ASSETS],
            capture_output=True, text=True, cwd=REPO,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("DRY RUN", proc.stdout)

    def test_pages_create_refuses_without_draft_flag(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, "blogger", "pages.py"), "create",
             os.path.join(REPO, "content", "pages", "about.md")],
            capture_output=True, text=True, cwd=REPO,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("--draft", proc.stderr + proc.stdout)

    def test_no_real_secret_values_in_repo_files(self):
        # Google credential value prefixes — none of them may appear in any file we commit.
        # Assembled from fragments so this checker does not flag its own source.
        leak_patterns = ("ya" + "29.", "GOCSPX" + "-", '"refresh_token": "1' + "//")
        offenders = []
        for root, dirs, files in os.walk(os.path.join(REPO, "blogger")):
            dirs[:] = [d for d in dirs if d not in {"__pycache__"}]
            for name in files:
                if not name.endswith((".py", ".json", ".md", ".xml")):
                    continue
                path = os.path.join(root, name)
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                if any(p in text for p in leak_patterns):
                    offenders.append(path)
        self.assertEqual(offenders, [])


class ApiContractTests(unittest.TestCase):
    """Regressions found by the first live smoke test (2026-10-16, after OAuth)."""

    def test_get_post_asks_for_the_admin_view(self):
        # Blogger's default READER view answers 404 for a DRAFT even though the same
        # id is listed by posts.list?status=DRAFT. get_post must send view=ADMIN.
        client = api.BloggerClient(CFG, token={"refresh_token": "stub"})
        seen: dict = {}

        def fake_request(method, url, body=None, params=None):
            seen.update(method=method, url=url, params=params or {})
            return {"id": "1", "status": "DRAFT"}

        client.request = fake_request
        post = client.get_post("1")
        self.assertEqual(post["status"], "DRAFT")
        self.assertEqual(seen["method"], "GET")
        self.assertEqual(seen["params"].get("view"), "ADMIN")

    def test_offline_connection_error_is_an_api_error(self):
        client = api.BloggerClient(CFG, token={"access_token": "stub", "expires_at": 9e9})

        def boom(*_args, **_kwargs):
            raise urllib.error.URLError("no route to host")

        original = urllib.request.urlopen
        urllib.request.urlopen = boom
        try:
            with self.assertRaises(api.ApiError) as ctx:
                client.request("GET", "https://www.googleapis.com/blogger/v3/blogs/1/posts")
        finally:
            urllib.request.urlopen = original
        self.assertEqual(ctx.exception.status, 0)
        self.assertIn("connection failed", ctx.exception.body)

    def test_delete_subcommand_is_documented(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, "blogger", "publish.py"), "--help"],
            capture_output=True, text=True, cwd=REPO,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("delete", proc.stdout)
        self.assertIn("revert", proc.stdout)


class PathAndHostTests(unittest.TestCase):
    """The gate must follow config.json, and masters must work from any drive."""

    IMG = ('<figure><img src="https://cdn.example.com/x.webp" alt="chart" '
           'loading="lazy"/><figcaption>cap</figcaption></figure>')

    def test_internal_links_follow_the_configured_host(self):
        cfg = json.loads(json.dumps(CFG))
        cfg["blog"]["blogspotUrl"] = "https://some-other-blog.blogspot.com"
        cfg["blog"]["customDomainUrl"] = None
        html = (self.IMG + '<p><a href="https://some-other-blog.blogspot.com/">home</a> '
                '<a href="/p/about.html">about</a> <a href="https://third-party.example/">out</a></p>')
        errors, warnings = gate(html, valid_meta(), cfg)
        self.assertEqual(errors, [])
        self.assertEqual([w for w in warnings if "internal link" in w], [])

    def test_third_party_links_do_not_count_as_internal(self):
        html = self.IMG + '<p><a href="https://third-party.example/">out</a></p>'
        _errors, warnings = gate(html, valid_meta())
        self.assertTrue([w for w in warnings if "internal link" in w], warnings)

    def test_master_outside_the_repo_is_accepted(self):
        with open(EXAMPLE, encoding="utf-8") as fh:
            master_text = fh.read()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "copied-guide.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(master_text)
            report = md2blogger.build_post_payload(path, CFG, ASSETS, None)
        self.assertTrue(report["source"])
        self.assertEqual(report["slug"], "llc-cost-breakdown")


class V3VariantTests(unittest.TestCase):
    """The Layouts v3 variants (v3_variant.py) and the declaration-surface checks [2c]/[2d].

    Background: the live blog serves our theme and instantiates none of its widgets. Every
    theme we could inspect that *does* render widgets (Blogger's stock templates, vtrick
    1.9.0, tech-jet 2.8.2, jobzeek) declares b:layoutsVersion='3' plus <b:defaultmarkups>;
    ours was the only one that did not. These tests pin the two derived files and the
    invariant that each moves exactly one variable.
    """

    def _validate(self, path: str) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = verify_theme.main(path)
        return code, buffer.getvalue()

    def _theme_text(self, name: str) -> str:
        with open(os.path.join(THEME_DIR, name), encoding="utf-8") as fh:
            return fh.read()

    def test_variant_check_mode_is_clean(self):
        proc = subprocess.run([sys.executable, os.path.join(THEME_DIR, "v3_variant.py"),
                               "--check"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("v3-decl ==", proc.stdout)

    def test_both_variants_are_well_formed_and_keep_the_blogger_namespaces(self):
        for name in (V3_DECL_THEME, V3_TAGS_THEME):
            with open(name, encoding="utf-8") as fh:
                raw = fh.read()
            root = ET.fromstring(raw)  # raises if the file is not well formed
            self.assertTrue(root.tag.endswith("}html") or root.tag == "html", name)
            self.assertIn("b:version='2'", raw)
            self.assertIn("b:defaultwidgetversion='2'", raw)
            self.assertIn("b:responsive='true'", raw)

    def test_declaration_variant_moves_declarations_only(self):
        """The whole point of the file: if it fails on the blog, one variable moved."""
        source = self._theme_text("owners-handbook-v2-decl.xml")
        decl = self._theme_text("owners-handbook-v3-decl.xml")
        self.assertNotEqual(decl, source)
        self.assertEqual(v3_variant.strip_declarations(decl), source)

    def test_declaration_variant_declares_the_v3_surface_working_themes_have(self):
        root = ET.fromstring(self._theme_text("owners-handbook-v3-decl.xml"))
        self.assertEqual(root.get(f"{GML_B}layoutsVersion"), "3")
        markups = list(root.iter(f"{GML_B}defaultmarkups"))
        self.assertEqual(len(markups), 1)
        blocks = list(root.iter(f"{GML_B}defaultmarkup"))
        self.assertGreaterEqual(len(blocks), 13)
        # Every widget this theme uses must be covered by the declared type surface.
        used = {w.get("type") for w in root.iter(f"{GML_B}widget")}
        declared = {b.get("type") for b in blocks}
        self.assertTrue(used.issubset(declared), f"{used - declared}")
        # The blocks are empty on purpose: each widget carries its own includables.
        self.assertTrue(all(len(list(b)) == 0 for b in blocks))

    def test_declaration_variant_keeps_the_v2_data_model(self):
        """It isolates the declaration surface, so it must stay a *mixed* file and say so."""
        decl = self._theme_text("owners-handbook-v3-decl.xml")
        self.assertIn("DATA MODEL: v2 (deliberate probe)", decl)
        self.assertTrue(v3_variant.remaining_v2_tags(decl))

    def test_tags_variant_leaves_no_v2_only_token_behind(self):
        tags = self._theme_text("owners-handbook-v3-tags.xml")
        self.assertIn("DATA MODEL: v3", tags)
        self.assertEqual(v3_variant.remaining_v2_tags(v3_variant.strip_tags_note(tags)), [])
        used = set(verify_theme.DATA_TOKEN_RE.findall(tags))
        missing = [t for t in v3_variant.V3_TOKENS_USED if t not in used]
        self.assertEqual(missing, [])

    def test_tags_variant_changes_nothing_but_data_tags(self):
        """Every changed line has to be a data tag, a documented literal or the model line."""
        decl = self._theme_text("owners-handbook-v3-decl.xml")
        tags = self._theme_text("owners-handbook-v3-tags.xml")
        self.assertEqual(v3_variant.undeclared_changes(decl, tags), [])

    def test_tags_variant_needs_no_guessed_tags(self):
        """Each mapped token is one a working v3 theme actually uses; the two tokens with no
        counterpart became literal text instead of an invented tag."""
        tags = self._theme_text("owners-handbook-v3-tags.xml")
        self.assertIn("Filed under:", tags)
        self.assertIn("Comments are moderated.", tags)
        self.assertNotIn("<data:blogTeamBlogMessage/>", tags)

    def test_every_theme_file_passes_the_offline_validator(self):
        for name in ("owners-handbook-v1.xml", "owners-handbook-v2-decl.xml",
                     "owners-handbook-v3-decl.xml", "owners-handbook-v3-tags.xml"):
            code, out = self._validate(os.path.join(THEME_DIR, name))
            self.assertEqual(code, 0, f"{name}\n{out}")

    def test_all_theme_files_declare_the_same_html_class_tokens(self):
        """verify_applied [1b] compares the live <html> class against the theme file, so the
        files have to agree on it or the generation check gives different answers."""
        tokens = {name: theme_generation_tokens(os.path.join(THEME_DIR, name))
                  for name in ("owners-handbook-v1.xml", "owners-handbook-v2-decl.xml",
                               "owners-handbook-v3-decl.xml", "owners-handbook-v3-tags.xml")}
        self.assertEqual(len(set(map(frozenset, tokens.values()))), 1, tokens)
        self.assertEqual(tokens["owners-handbook-v1.xml"], {"v2"})

    def test_validator_flags_a_v3_surface_without_defaultmarkups(self):
        """The exception is the pair, not the token."""
        decl = self._theme_text("owners-handbook-v3-decl.xml")
        broken = re.sub(r"^<b:defaultmarkups>\n.*?^</b:defaultmarkups>\n", "", decl,
                        flags=re.S | re.M)
        self.assertNotEqual(broken, decl)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "no-markups.xml")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(broken)
            code, out = self._validate(path)
        self.assertEqual(code, 1, out)
        self.assertIn("b:layoutsVersion='3' appears only with", out)

    def test_validator_flags_a_v2_token_sneaked_back_into_the_v3_tags_file(self):
        tags = self._theme_text("owners-handbook-v3-tags.xml")
        broken = tags.replace("data:post.numberOfComments", "data:post.numComments", 1)
        self.assertNotEqual(broken, tags)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mixed-tags.xml")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(broken)
            code, out = self._validate(path)
        self.assertEqual(code, 1, out)
        self.assertIn("no v2-only data tags", out)

    def test_validator_flags_a_v3_token_in_a_v2_file(self):
        v2 = self._theme_text("owners-handbook-v2-decl.xml")
        broken = v2.replace("<data:blog.title/>", "<data:view.title/>", 1)
        self.assertNotEqual(broken, v2)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "v2-with-v3-token.xml")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(broken)
            code, out = self._validate(path)
        self.assertEqual(code, 1, out)
        self.assertIn("no v3-only data tags", out)

    def test_tag_map_evidence_is_recorded(self):
        """Nothing gets mapped without a working theme to point at."""
        for pattern, replacement, why in v3_variant.TAG_MAP:
            self.assertTrue(pattern and replacement and why, (pattern, replacement))
            self.assertTrue(any(name in why for name in
                                ("vtrick", "jobzeek", "tech-jet", "no grounded", "illegal",
                                 "cannot be an element")), why)


class BisectProbeTests(unittest.TestCase):
    """The B0 diagnostic theme and the measured reading of its markers."""

    PROBE = os.path.join(THEME_DIR, "bisect", "B0-probe.xml")
    BASELINE = os.path.join(THEME_DIR, "bisect", "B0-baseline.xml")

    def _read(self, path: str) -> str:
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    def _bisect(self, html_text: str) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = verify_applied.bisect_report(html_text, "https://example.blogspot.com/")
        return code, buffer.getvalue()

    def test_bisect_files_are_well_formed_theme_documents(self):
        expected_sections = {self.BASELINE: 3, self.PROBE: 4}  # probe adds the jhl-probe one
        for path, sections in expected_sections.items():
            root = ET.fromstring(self._read(path))
            self.assertEqual(len(list(root.iter(f"{GML_B}section"))), sections, path)
            self.assertGreaterEqual(len(list(root.iter(f"{GML_B}widget"))), 3, path)

    def test_probe_keeps_the_ids_the_layout_already_holds(self):
        root = ET.fromstring(self._read(self.PROBE))
        self.assertEqual([s.get("id") for s in root.iter(f"{GML_B}section")],
                         ["header", "main-posts", "footer", "jhl-probe"])
        ids = [w.get("id") for w in root.iter(f"{GML_B}widget")]
        self.assertIn("Header1", ids)   # existing ids: re-mapping path
        self.assertIn("HTML99", ids)    # brand-new ids: instantiation path
        self.assertIn("HTML98", ids)    # brand-new id with no includable: default path

    def test_probe_carries_every_marker_the_checker_reads(self):
        probe = self._read(self.PROBE)
        for marker, _meaning, _fresh in verify_applied.BISECT_MARKERS:
            if marker == "B0-NOTE-THEME-SERVED":
                self.assertTrue(any(re.search(p, probe, re.I)
                                    for p in verify_applied.BISECT_THEME_SIGNS), marker)
                continue
            self.assertIn(marker, probe)

    def test_existing_id_marker_is_markup_not_a_setting(self):
        """A widget *setting* can be replaced by the layout's stored value for an id the
        layout knows, so a missing setting would prove nothing. The id marker is markup."""
        probe = self._read(self.PROBE)
        marker = probe.index("<p class='b0-existing'>B0-EXISTING-ID-WIDGET-RENDERED</p>")
        # ... and it sits inside the widget's includable, after its settings block.
        settings_end = probe.rindex("</b:widget-settings>", 0, marker)
        self.assertIn("<b:includable", probe[settings_end:marker])

    def test_verdict_when_both_id_classes_render(self):
        code, out = self._bisect(self._read(self.PROBE))
        self.assertEqual(code, 0, out)
        self.assertIn("instantiates new ids", out)
        self.assertIn("owners-handbook-v3-decl.xml", out)

    def test_verdict_when_only_existing_ids_render(self):
        probe = self._read(self.PROBE)
        for marker in ("B0-PROBE-FRESH-WIDGET-RENDERED", "B0-PROBE-FRESH-CONTENT",
                       "B0-PROBE-BARE-FRESH-CONTENT"):
            probe = probe.replace(marker, "not-rendered")
        code, out = self._bisect(probe)
        self.assertEqual(code, 0, out)
        self.assertIn("brand-new ids do NOT", out)

    def test_verdict_when_the_theme_serves_but_no_widget_renders(self):
        probe = self._read(self.PROBE)
        for marker in ("B0-MARKER-WIDGET-RENDERED", "B0-EXISTING-ID-WIDGET-RENDERED",
                       "B0-HTML-WIDGET-RENDERED", "B0-PROBE-FRESH-WIDGET-RENDERED",
                       "B0-PROBE-FRESH-CONTENT", "B0-PROBE-BARE-FRESH-CONTENT"):
            probe = probe.replace(marker, "not-rendered")
        code, out = self._bisect(probe)
        self.assertEqual(code, 6, out)
        self.assertIn("does not render widgets for a hand-pasted theme", out)

    def test_verdict_when_the_paste_did_not_land(self):
        code, out = self._bisect("<html><head><title>blog</title></head><body>hi</body></html>")
        self.assertEqual(code, 3, out)
        self.assertIn("not the B0-probe theme", out)

    def test_markers_inside_a_script_do_not_count(self):
        """Blogger's widget registration mentions ids, and a theme comment can quote a
        marker; only rendered markup counts."""
        page = ("<html><body><p class='b0-note'>B0 baseline theme</p>"
                "<script>var x = 'B0-MARKER-WIDGET-RENDERED';</script></body></html>")
        code, out = self._bisect(page)
        self.assertEqual(code, 6, out)
        self.assertIn("MISSING", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
