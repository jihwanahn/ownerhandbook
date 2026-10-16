// SVG/raster -> WebP at a fixed width, using sharp (libvips).
//
// Why this exists: Blogger's API has no image upload, so guides reference images
// hosted elsewhere (GitHub Pages in Phase 2). Every published image must be WebP and
// 1200px wide (blogger/images/IMAGE-RULES.md), and sharp does the SVG rasterisation
// and the encode in one call with no extra system dependencies.
//
// Usage:
//   node blogger/images/to_webp.mjs out.webp in.svg [in.png ...]
//   node blogger/images/to_webp.mjs out.webp in.svg --width 1200 --quality 82

import sharp from "sharp";

const args = process.argv.slice(2);
const opts = { width: 1200, quality: 82 };
const positional = [];
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--width") opts.width = Number(args[++i]);
  else if (args[i] === "--quality") opts.quality = Number(args[++i]);
  else positional.push(args[i]);
}
const [out, ...inputs] = positional;
if (!out || inputs.length === 0) {
  console.error("usage: node to_webp.mjs out.webp in.svg [in.png ...] [--width 1200] [--quality 82]");
  process.exit(2);
}

const base = sharp(inputs[0], { density: 192 }).resize({ width: opts.width, withoutEnlargement: false });
const pipeline = inputs.length > 1
  ? base.composite(await Promise.all(inputs.slice(1).map(async (p, i) => ({
      input: await sharp(p).resize({ width: opts.width }).toBuffer(),
      top: 0, left: 0,
    }))))
  : base;

const info = await pipeline.webp({ quality: opts.quality, effort: 5 }).toFile(out);
console.log(JSON.stringify({ out, width: info.width, height: info.height, bytes: info.size }));
