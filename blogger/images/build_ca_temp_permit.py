#!/usr/bin/env python3
"""New original diagrams for the 2026-11-14 craft-fair manuscript.

Not recovered assets. Run from the repository with PYTHONIOENCODING=utf-8.
All foreground content is contained in x150..1050 / y30..600 on 1200x630.
SVG intermediates are generated in the existing ignored build directory.
"""
from pathlib import Path
import html
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BUILD = HERE / "build" / "ca-temp-permit"
ASSETS = ROOT / "assets" / "images"


def text(x, y, value, size=26, fill="#173b2b", weight=400):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}">{html.escape(value)}</text>')


def rect(x, y, width, height, fill):
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="18" fill="{fill}"/>'


def canvas(title, subtitle, contents, source):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">'
            '<rect width="1200" height="630" fill="#f6f4ed"/>'
            '<g font-family="Arial, sans-serif">'
            + text(160, 72, "THE OWNER'S HANDBOOK  /  CALIFORNIA CRAFT FAIRS", 18, weight=700)
            + text(160, 133, title, 43, weight=700)
            + text(160, 177, subtitle, 23, fill="#52665b")
            + contents
            + text(160, 578, source, 16, fill="#52665b")
            + text(160, 600, "Original diagram | Official guidance checked November 14, 2026", 16, fill="#52665b")
            + '</g></svg>')


def route():
    parts = rect(160, 210, 880, 148, "#1f4d3a")
    parts += text(185, 249, "ALREADY HAVE A PERMANENT-LOCATION PERMIT?", 20, "#d5e8dc", 700)
    parts += text(185, 296, "Register the event sub-permit", 34, "#ffffff", 700)
    parts += text(185, 332, "Use the existing CDTFA account for the temporary location.", 22, "#ffffff")
    parts += rect(160, 378, 880, 148, "#e3e9df")
    parts += text(185, 417, "NO PERMANENT PLACE OF BUSINESS?", 20, weight=700)
    parts += text(185, 464, "Check temporary seller registration", 33, weight=700)
    parts += text(185, 500, "Use the fair address and the selling dates CDTFA approves.", 22)
    return canvas("Which seller's permit?", "Two starting points for a short event selling taxable crafts.", parts,
                  "Sources: CDTFA Temporary Sellers; state-designated fairgrounds guide")


def paperwork():
    rows = [
        (212, "01", "REGISTER WITH CDTFA", "Get the correct permit for the event location."),
        (322, "02", "DOCUMENT YOUR STATUS", "Give the operator the required seller information."),
        (432, "03", "FILE THE REQUIRED RETURN", "Keep event records and check your account's due date."),
    ]
    parts = ""
    for y, number, title, detail in rows:
        parts += rect(160, y, 880, 94, "#e3e9df")
        parts += text(181, y + 57, number, 34, weight=700)
        parts += text(260, y + 35, title, 21, weight=700)
        parts += text(260, y + 68, detail, 23)
    return canvas("Three separate tasks", "Organizer paperwork does not replace a seller's permit.", parts,
                  "Sources: CDTFA Publication 111; Temporary Sellers guide")


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name, diagram in [
        ("california-craft-fair-permit-route", route()),
        ("california-craft-fair-paperwork", paperwork()),
    ]:
        svg = BUILD / f"{name}.svg"
        svg.write_text(diagram, encoding="utf-8")
        subprocess.run(["node", str(HERE / "to_webp.mjs"), str(ASSETS / f"{name}.webp"), str(svg)],
                       check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
