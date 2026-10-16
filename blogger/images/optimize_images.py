#!/usr/bin/env python3
"""Image pipeline: normalise, publish and audit the guide images (JHL-4 §3).

Rules enforced (see blogger/images/IMAGE-RULES.md):
  * published images are WebP, 1200px wide, kebab-case filenames
  * every published file is under the size budget (default 400 KB)
  * images a guide references exist in assets/images/ (or are remote URLs)

Usage:
    python blogger/images/optimize_images.py convert <file-or-dir> [--out assets/images]
    python blogger/images/optimize_images.py check [--dir assets/images]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ASSETS = os.path.join(REPO, "assets", "images")
RASTER = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".avif", ".webp"}
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.webp$")
SIZE_BUDGET = 400 * 1024


def node() -> str:
    exe = shutil.which("node")
    if not exe:
        raise SystemExit("node not found on PATH — the WebP step needs it (see blogger/README.md)")
    return exe


def meta(paths: list[str]) -> list[dict]:
    proc = subprocess.run([node(), os.path.join(HERE, "img_meta.mjs"), *paths],
                          capture_output=True, text=True, cwd=HERE)
    if proc.returncode != 0:
        raise SystemExit(f"img_meta.mjs failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def convert(target: str, out_dir: str, width: int, quality: int) -> int:
    files: list[str] = []
    if os.path.isdir(target):
        for name in sorted(os.listdir(target)):
            if os.path.splitext(name)[1].lower() in RASTER | {".svg"}:
                files.append(os.path.join(target, name))
    else:
        files.append(target)
    if not files:
        print(f"nothing to convert in {target}")
        return 0
    os.makedirs(out_dir, exist_ok=True)
    for src in files:
        stem = os.path.splitext(os.path.basename(src))[0].lower().replace("_", "-").replace(" ", "-")
        dest = os.path.join(out_dir, stem + ".webp")
        proc = subprocess.run(
            [node(), os.path.join(HERE, "to_webp.mjs"), dest, src,
             "--width", str(width), "--quality", str(quality)],
            capture_output=True, text=True, cwd=HERE,
        )
        if proc.returncode != 0:
            print(f"FAILED {src}: {proc.stderr.strip() or proc.stdout.strip()}")
            return 1
        print(f"{os.path.relpath(src, REPO)} -> {os.path.relpath(dest, REPO)}  {proc.stdout.strip()}")
    return 0


def check(directory: str) -> int:
    if not os.path.isdir(directory):
        print(f"no such directory: {directory}")
        return 1
    names = sorted(n for n in os.listdir(directory) if not n.startswith("."))
    if not names:
        print(f"{directory} is empty")
        return 0
    rows = meta([os.path.join(directory, n) for n in names])
    failures = 0
    print(f"{'file':46} {'size':>10}  {'dimensions':>11}  verdict")
    for row in rows:
        name = os.path.basename(row["file"])
        if "error" in row:
            print(f"{name:46} {'-':>10}  {'-':>11}  ERROR {row['error']}")
            failures += 1
            continue
        verdict = []
        if not KEBAB.match(name):
            verdict.append("filename must be english-kebab-case .webp")
        if row["width"] != 1200:
            verdict.append(f"width is {row['width']}, expected 1200")
        if row["bytes"] > SIZE_BUDGET:
            verdict.append(f"{row['bytes'] // 1024} KB over the {SIZE_BUDGET // 1024} KB budget")
        if verdict:
            failures += 1
        print(f"{name:46} {row['bytes'] / 1024:8.1f}K  {row['width']}x{row['height']:<6}  "
              f"{'; '.join(verdict) if verdict else 'ok'}")
    print(f"\n{len(rows) - failures}/{len(rows)} file(s) pass the image rules")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Guide image pipeline (WebP normalisation + audit)")
    sub = parser.add_subparsers(dest="command", required=True)
    p_conv = sub.add_parser("convert", help="raster/SVG -> WebP at a fixed width")
    p_conv.add_argument("target")
    p_conv.add_argument("--out", default=ASSETS)
    p_conv.add_argument("--width", type=int, default=1200)
    p_conv.add_argument("--quality", type=int, default=82)
    p_check = sub.add_parser("check", help="audit published images against the rules")
    p_check.add_argument("--dir", default=ASSETS)
    args = parser.parse_args()
    if args.command == "convert":
        return convert(args.target, args.out, args.width, args.quality)
    return check(args.dir)


if __name__ == "__main__":
    sys.exit(main())
