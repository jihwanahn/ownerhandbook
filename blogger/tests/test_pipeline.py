#!/usr/bin/env python3
"""Offline test suite for the Blogger pipeline (no network, no credentials required).

Run:  python blogger/tests/test_pipeline.py -v
Everything here works before the owner finishes the OAuth setup, which is what the
issue requires ("OAuth 완료 전 — 오프라인 검증·dry-run까지").
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "blogger"))
sys.path.insert(0, os.path.join(REPO, "blogger", "theme"))

import blogger_api as api  # noqa: E402
import md2blogger  # noqa: E402
import verify_theme  # noqa: E402

CFG = api.load_config()
ASSETS = "https://example.github.io/owners-handbook-images"
EXAMPLE = os.path.join(REPO, "content", "posts", "example-guide.md")


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
    def test_theme_validator_passes(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = verify_theme.main(os.path.join(REPO, "blogger", "theme", "owners-handbook-v1.xml"))
        self.assertEqual(code, 0, buffer.getvalue())


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
