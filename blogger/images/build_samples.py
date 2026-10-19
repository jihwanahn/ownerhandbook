#!/usr/bin/env python3
"""Generate the self-produced explanatory diagrams for The Owner's Handbook.

Two of the three JHL-4 §3 samples are code-drawn SVG: diagrams/charts are produced
from this script rather than AI generation because they are deterministic, diffable,
tiny, and can carry real numbers the moment a guide's figures are verified.

Output: blogger/images/samples/*.svg  (source of truth)
        blogger/images/samples/*.webp (published form; built by to_webp.mjs)

Palette and type scale are shared with the Blogger theme so an article's figures do
not look pasted in from another site.

Usage: python blogger/images/build_samples.py [--no-webp]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(HERE, "samples")

INK = "#1f2328"
INK_SOFT = "#5b6470"
LINE = "#e4e7eb"
ACCENT = "#14532d"
ACCENT_2 = "#2f855a"
ACCENT_3 = "#94a89b"
BG = "#ffffff"
BG_SOFT = "#f7f8fa"
WARN = "#8a5a00"

FONT = "Segoe UI, Helvetica Neue, Arial, sans-serif"

# Figures in the explanatory diagrams are citations, not decoration. Every number
# drawn here must be traceable to the filing agency that charges it; the source line
# under each figure names the agency class. See blogger/images/IMAGE-RULES.md §7.


def _svg(width: int, height: int, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">\n'
        f'  <rect width="{width}" height="{height}" fill="{BG}"/>\n'
        f"{body}\n</svg>\n"
    )


def filing_fee_chart() -> str:
    """Horizontal bar chart: LLC filing fee by state, primary-source values.

    Verified 2026-10-19 against each state's own fee schedule (the numbers a filer is
    actually charged by the secretary of state, not a comparison site's summary):
    MA $500 (sec.state.ma.us), TX $300 (sos.state.tx.us), NY $200 (dos.ny.gov; the
    $205 quoted elsewhere adds a $5 plain-copy fee), FL $125 (dos.fl.gov — $100 filing
    + $25 registered agent), WY $100 (sos.wyo.gov), CA $70 (sos.ca.gov).
    """
    w, h = 1200, 720
    rows = [
        ("Massachusetts", 500),
        ("Texas", 300),
        ("New York", 200),
        ("Florida", 125),
        ("Wyoming", 100),
        ("California", 70),
    ]
    max_val = 500
    left, top = 300, 170
    bar_h, gap = 46, 26
    plot_w = w - left - 130

    parts = [
        f'  <text x="64" y="86" font-family="{FONT}" font-size="40" font-weight="700" fill="{INK}">'
        "What an LLC costs to file</text>",
        f'  <text x="64" y="124" font-family="{FONT}" font-size="22" fill="{INK_SOFT}">'
        "State filing fee, US dollars, 2026</text>",
        f'  <line x1="64" y1="150" x2="{w - 64}" y2="150" stroke="{LINE}" stroke-width="2"/>',
    ]
    for i, (state, value) in enumerate(rows):
        y = top + i * (bar_h + gap)
        bar_w = int(plot_w * value / max_val)
        shade = ACCENT if i in (0, len(rows) - 1) else ACCENT_2 if value >= 200 else ACCENT_3
        parts += [
            f'  <text x="64" y="{y + 31}" font-family="{FONT}" font-size="24" fill="{INK}">{state}</text>',
            f'  <rect x="{left}" y="{y}" width="{bar_w}" height="{bar_h}" rx="3" fill="{shade}"/>',
            f'  <text x="{left + bar_w + 16}" y="{y + 31}" font-family="{FONT}" font-size="24" '
            f'font-weight="600" fill="{INK}">${value}</text>',
        ]
    parts += [
        f'  <line x1="{left}" y1="{top + 6 * (bar_h + gap) - gap + 10}" x2="{w - 64}" '
        f'y2="{top + 6 * (bar_h + gap) - gap + 10}" stroke="{LINE}" stroke-width="2"/>',
        f'  <text x="64" y="{h - 40}" font-family="{FONT}" font-size="19" fill="{INK_SOFT}">'
        "Source: each state&#39;s secretary of state fee schedule, 2026.</text>",
    ]
    return _svg(w, h, "\n".join(parts))


def first_90_days_timeline() -> str:
    """Milestone timeline for the first 90 days after formation."""
    w, h = 1200, 620
    milestones = [
        ("Day 0", "Formation filed", "Articles of organization accepted, EIN applied for"),
        ("Day 30", "Bank and records", "Business account opened, receipts filed from day one"),
        ("Day 60", "Licenses and permits", "Local business license, sales tax registration if selling goods"),
        ("Day 90", "Habits that stick", "Monthly close, quarterly estimates reserved"),
    ]
    top = 320
    parts = [
        f'  <text x="64" y="86" font-family="{FONT}" font-size="40" font-weight="700" fill="{INK}">'
        "The first 90 days</text>",
        f'  <text x="64" y="124" font-family="{FONT}" font-size="22" fill="{INK_SOFT}">'
        "What actually has a deadline after you form the company</text>",
        f'  <line x1="210" y1="{top}" x2="{w - 210}" y2="{top}" stroke="{LINE}" stroke-width="6"/>',
    ]
    step = (w - 420) / (len(milestones) - 1)
    for i, (day, title, detail) in enumerate(milestones):
        x = int(210 + i * step)
        parts += [
            f'  <circle cx="{x}" cy="{top}" r="16" fill="{ACCENT}"/>',
            f'  <circle cx="{x}" cy="{top}" r="7" fill="{BG}"/>',
            f'  <text x="{x}" y="{top - 46}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="26" font-weight="700" fill="{ACCENT}">{day}</text>',
            f'  <text x="{x}" y="{top + 62}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="23" font-weight="600" fill="{INK}">{title}</text>',
        ]
        words = detail.split()
        lines, current = [], ""
        for word in words:
            if len(current) + len(word) > 26:
                lines.append(current)
                current = word
            else:
                current = (current + " " + word).strip()
        lines.append(current)
        for j, line in enumerate(lines):
            parts.append(
                f'  <text x="{x}" y="{top + 96 + j * 28}" text-anchor="middle" '
                f'font-family="{FONT}" font-size="20" fill="{INK_SOFT}">{line}</text>'
            )
    return _svg(w, h, "\n".join(parts))


def cartoon_meme() -> str:
    """Third sample: the house style for a self-made humour image (no stock, no memes
    of other people's work — drawn here as an SVG so the file is ours outright)."""
    w, h = 1200, 620
    parts = [
        f'  <rect width="{w}" height="{h}" fill="{BG_SOFT}"/>',
        f'  <text x="64" y="96" font-family="{FONT}" font-size="40" font-weight="700" fill="{INK}">'
        "&#34;My cousin says I don&#39;t need an LLC&#34;</text>",
        f'  <text x="64" y="140" font-family="{FONT}" font-size="24" fill="{INK_SOFT}">'
        "A helpful-relative risk assessment, in two panels</text>",
        # left panel
        f'  <rect x="64" y="190" width="520" height="300" rx="14" fill="{BG}" stroke="{LINE}" stroke-width="3"/>',
        f'  <circle cx="160" cy="290" r="34" fill="{ACCENT_3}"/>',
        f'  <path d="M126 400 q34 -60 68 0 z" fill="{ACCENT_3}"/>',
        f'  <text x="240" y="280" font-family="{FONT}" font-size="26" fill="{INK}">Cousin,&#160;unprompted:</text>',
        f'  <text x="240" y="322" font-family="{FONT}" font-size="24" fill="{INK_SOFT}">'
        "&#34;You don&#39;t need that, just</text>",
        f'  <text x="240" y="356" font-family="{FONT}" font-size="24" fill="{INK_SOFT}">'
        "keep it simple, trust me.&#34;</text>",
        f'  <text x="96" y="462" font-family="{FONT}" font-size="22" font-weight="600" fill="{WARN}">'
        "Cost: 0 minutes, 1 opinion</text>",
        # right panel
        f'  <rect x="616" y="190" width="520" height="300" rx="14" fill="{BG}" stroke="{LINE}" stroke-width="3"/>',
        f'  <rect x="660" y="230" width="432" height="52" rx="8" fill="{BG_SOFT}" stroke="{LINE}" stroke-width="2"/>',
        f'  <text x="680" y="265" font-family="{FONT}" font-size="24" fill="{INK}">Liability, uncovered</text>',
        f'  <text x="680" y="330" font-family="{FONT}" font-size="26" fill="{INK}">Personal assets</text>',
        f'  <text x="680" y="374" font-family="{FONT}" font-size="26" fill="{INK}">on the line</text>',
        f'  <text x="680" y="436" font-family="{FONT}" font-size="30" font-weight="700" fill="{WARN}">'
        "The fix costs more</text>",
        f'  <text x="680" y="474" font-family="{FONT}" font-size="30" font-weight="700" fill="{WARN}">'
        "than the LLC did</text>",
        f'  <text x="64" y="{h - 40}" font-family="{FONT}" font-size="22" fill="{INK_SOFT}">'
        "House rule: humour images are drawn or generated in-house. No third-party memes.</text>",
    ]
    return _svg(w, h, "\n".join(parts))


def ein_paperwork_order() -> str:
    """Timeline: where the EIN sits in the paperwork order. No invented numbers —
    the only figures drawn are 'free', 'immediate' and the step numbers, all from
    the IRS pages named in the source line."""
    w, h = 1200, 600
    milestones = [
        ("Step 1", "Form the entity", "The state accepts your LLC, corporation or partnership filing"),
        ("Step 2", "Get the EIN", "Free from the IRS, issued immediately online"),
        ("Step 3", "Open the bank account", "Banks ask for the EIN and the formation documents"),
        ("Step 4", "Pay people", "Payroll returns, W-9 requests and 1099 forms need the number"),
    ]
    top = 310
    parts = [
        f'  <text x="64" y="86" font-family="{FONT}" font-size="40" font-weight="700" fill="{INK}">'
        "The EIN comes third</text>",
        f'  <text x="64" y="124" font-family="{FONT}" font-size="22" fill="{INK_SOFT}">'
        "Four steps, and the order is not optional</text>",
        f'  <line x1="210" y1="{top}" x2="{w - 210}" y2="{top}" stroke="{LINE}" stroke-width="6"/>',
    ]
    step = (w - 420) / (len(milestones) - 1)
    for i, (day, title, detail) in enumerate(milestones):
        x = int(210 + i * step)
        parts += [
            f'  <circle cx="{x}" cy="{top}" r="16" fill="{ACCENT}"/>',
            f'  <circle cx="{x}" cy="{top}" r="7" fill="{BG}"/>',
            f'  <text x="{x}" y="{top - 46}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="26" font-weight="700" fill="{ACCENT}">{day}</text>',
            f'  <text x="{x}" y="{top + 62}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="23" font-weight="600" fill="{INK}">{title}</text>',
        ]
        lines, current = [], ""
        for word in detail.split():
            if len(current) + len(word) > 26:
                lines.append(current)
                current = word
            else:
                current = (current + " " + word).strip()
        lines.append(current)
        for j, line in enumerate(lines):
            parts.append(
                f'  <text x="{x}" y="{top + 96 + j * 28}" text-anchor="middle" '
                f'font-family="{FONT}" font-size="20" fill="{INK_SOFT}">{line}</text>'
            )
    parts.append(
        f'  <text x="64" y="{h - 40}" font-family="{FONT}" font-size="19" fill="{INK_SOFT}">'
        "Source: IRS, &#34;Employer identification number&#34; and &#34;How to apply for an EIN&#34;; "
        "SBA, &#34;Launch your business&#34; (2026).</text>"
    )
    return _svg(w, h, "\n".join(parts))


def ein_wait_times() -> str:
    """Horizontal bar chart: how long each EIN route takes, in business days.

    Values are the IRS's own published turnarounds: online = issued immediately,
    fax = about 4 business days, mail = about 4 weeks (20 business days). The bars
    are drawn in business days so their relative length means something, and the
    printed label states the unit the IRS actually used.
    """
    w, h = 1200, 600
    rows = [
        ("Online", 0, "Issued immediately"),
        ("Fax Form SS-4", 4, "About 4 business days"),
        ("Mail Form SS-4", 20, "About 4 weeks"),
    ]
    max_val = 20
    left, top = 360, 200
    bar_h, gap = 52, 34
    plot_w = w - left - 420
    parts = [
        f'  <text x="64" y="86" font-family="{FONT}" font-size="40" font-weight="700" fill="{INK}">'
        "How long an EIN takes</text>",
        f'  <text x="64" y="124" font-family="{FONT}" font-size="22" fill="{INK_SOFT}">'
        "IRS-published turnaround by application route, 2026</text>",
        f'  <line x1="64" y1="152" x2="{w - 64}" y2="152" stroke="{LINE}" stroke-width="2"/>',
    ]
    for i, (label, value, printed) in enumerate(rows):
        y = top + i * (bar_h + gap)
        bar_w = max(int(plot_w * value / max_val), 4)
        shade = ACCENT if i == 0 else ACCENT_2 if i == 1 else ACCENT_3
        parts += [
            f'  <text x="64" y="{y + 34}" font-family="{FONT}" font-size="25" fill="{INK}">{label}</text>',
            f'  <rect x="{left}" y="{y}" width="{bar_w}" height="{bar_h}" rx="3" fill="{shade}"/>',
            f'  <text x="{left + bar_w + 18}" y="{y + 34}" font-family="{FONT}" font-size="25" '
            f'font-weight="600" fill="{INK}">{printed}</text>',
        ]
    parts += [
        f'  <line x1="64" y1="{top + 3 * (bar_h + gap) - gap + 14}" x2="{w - 64}" '
        f'y2="{top + 3 * (bar_h + gap) - gap + 14}" stroke="{LINE}" stroke-width="2"/>',
        f'  <text x="64" y="{h - 118}" font-family="{FONT}" font-size="19" fill="{INK_SOFT}">'
        "If your principal place of business is outside the U.S., the online tool is not available:</text>",
        f'  <text x="64" y="{h - 92}" font-family="{FONT}" font-size="19" fill="{INK_SOFT}">'
        "those applicants call 267-941-1099, 6 a.m.&#8211;11 p.m. ET, Monday&#8211;Friday.</text>",
        f'  <text x="64" y="{h - 40}" font-family="{FONT}" font-size="19" fill="{INK_SOFT}">'
        "Source: IRS, &#34;How to apply for an EIN&#34; and &#34;Employer identification number&#34;, 2026.</text>",
    ]
    return _svg(w, h, "\n".join(parts))


def ein_middleman() -> str:
    """Humour, style B (pure SVG, no generation step): the reseller next to the source.

    The only two figures drawn are $0 and 'issued immediately', both from the IRS
    page quoted under the panels — see blogger/images/IMAGE-RULES.md §7.
    """
    w, h = 1200, 620
    parts = [
        f'  <rect width="{w}" height="{h}" fill="{BG_SOFT}"/>',
        f'  <text x="64" y="96" font-family="{FONT}" font-size="40" font-weight="700" fill="{INK}">'
        "&#34;Professional EIN filing&#34;</text>",
        f'  <text x="64" y="140" font-family="{FONT}" font-size="24" fill="{INK_SOFT}">'
        "Two ways to get the same nine digits</text>",
        # left panel
        f'  <rect x="64" y="190" width="520" height="300" rx="14" fill="{BG}" stroke="{LINE}" stroke-width="3"/>',
        f'  <text x="96" y="244" font-family="{FONT}" font-size="26" font-weight="700" fill="{WARN}">'
        "A website that charges</text>",
        f'  <text x="96" y="296" font-family="{FONT}" font-size="23" fill="{INK}">'
        "Fills in Form SS-4 for you</text>",
        f'  <text x="96" y="336" font-family="{FONT}" font-size="23" fill="{INK}">'
        "Sends it to the IRS</text>",
        f'  <text x="96" y="376" font-family="{FONT}" font-size="23" fill="{INK}">'
        "You wait for the number</text>",
        f'  <text x="96" y="452" font-family="{FONT}" font-size="25" font-weight="600" fill="{WARN}">'
        "Cost: whatever it asks</text>",
        # right panel
        f'  <rect x="616" y="190" width="520" height="300" rx="14" fill="{BG}" stroke="{LINE}" stroke-width="3"/>',
        f'  <text x="648" y="244" font-family="{FONT}" font-size="26" font-weight="700" fill="{ACCENT}">'
        "irs.gov</text>",
        f'  <text x="648" y="296" font-family="{FONT}" font-size="23" fill="{INK}">'
        "You fill in Form SS-4</text>",
        f'  <text x="648" y="336" font-family="{FONT}" font-size="23" fill="{INK}">'
        "Issued immediately online</text>",
        f'  <text x="648" y="376" font-family="{FONT}" font-size="23" fill="{INK}">'
        "You print the confirmation</text>",
        f'  <text x="648" y="452" font-family="{FONT}" font-size="25" font-weight="600" fill="{ACCENT}">'
        "Cost: $0</text>",
        f'  <text x="64" y="{h - 78}" font-family="{FONT}" font-size="23" font-weight="600" fill="{INK}">'
        "The number is identical &#8212; there is one issuer and one EIN system.</text>",
        f'  <text x="64" y="{h - 40}" font-family="{FONT}" font-size="19" fill="{INK_SOFT}">'
        "Source: IRS, &#34;Get an employer identification number&#34;: you never have to pay a "
        "fee for an EIN.</text>",
    ]
    return _svg(w, h, "\n".join(parts))


BUILDERS = {
    "llc-filing-fee-breakdown": filing_fee_chart,
    "first-90-days-timeline": first_90_days_timeline,
    "helpful-relative-advice": cartoon_meme,
    "ein-paperwork-order": ein_paperwork_order,
    "ein-wait-times": ein_wait_times,
    "ein-middleman": ein_middleman,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the sample diagrams (SVG -> WebP)")
    parser.add_argument("--no-webp", action="store_true", help="only write the SVG sources")
    parser.add_argument("--width", type=int, default=1200)
    args = parser.parse_args()

    os.makedirs(SAMPLES, exist_ok=True)
    written = []
    for name, builder in BUILDERS.items():
        svg_path = os.path.join(SAMPLES, f"{name}.svg")
        with open(svg_path, "w", encoding="utf-8") as fh:
            fh.write(builder())
        written.append(svg_path)
        print(f"wrote {svg_path}")

    if args.no_webp:
        return 0

    node = shutil.which("node")
    if not node:
        print("node not found — skipping the WebP step (run `node to_webp.mjs` manually)")
        return 0
    for svg_path in written:
        webp_path = svg_path[:-4] + ".webp"
        proc = subprocess.run(
            [node, os.path.join(HERE, "to_webp.mjs"), webp_path, svg_path, "--width", str(args.width)],
            capture_output=True, text=True, cwd=HERE,
        )
        if proc.returncode != 0:
            print(f"FAILED {svg_path}: {proc.stderr.strip() or proc.stdout.strip()}")
            return 1
        print(f"wrote {webp_path}  {proc.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
