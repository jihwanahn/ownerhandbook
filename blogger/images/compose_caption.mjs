// Compose a self-made humour image: illustration + caption bands (our own words).
//
// The house rule (blogger/images/IMAGE-RULES.md) is that no third-party meme, stock
// photo or clip-art is ever published. Humour images are either drawn in SVG by
// build_samples.py or generated in-house and captioned here, so every pixel in the
// file is ours.
//
// Usage:
//   node blogger/images/compose_caption.mjs in.jpg out.webp \
//        --top "\"My cousin says I don't need an LLC\"" \
//        --bottom "Personal liability, still uncovered" \
//        --width 1200

import sharp from "sharp";

const args = process.argv.slice(2);
const opts = { width: 1200, top: "", bottom: "", font: 54 };
const positional = [];
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === "--top") opts.top = args[++i];
  else if (a === "--bottom") opts.bottom = args[++i];
  else if (a === "--width") opts.width = Number(args[++i]);
  else if (a === "--font") opts.font = Number(args[++i]);
  else positional.push(a);
}
const [input, output] = positional;
if (!input || !output) {
  console.error("usage: node compose_caption.mjs in.jpg out.webp [--top text] [--bottom text] [--width 1200]");
  process.exit(2);
}

const xml = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&apos;");

function wrap(text, perLine) {
  const words = text.split(/\s+/);
  const lines = [];
  let line = "";
  for (const w of words) {
    if ((line + " " + w).trim().length > perLine) { lines.push(line.trim()); line = w; }
    else line += " " + w;
  }
  if (line.trim()) lines.push(line.trim());
  return lines;
}

const base = sharp(input).resize({ width: opts.width });
const baseBuf = await base.toBuffer();
const { width: w, height: h } = await sharp(baseBuf).metadata();

const font = Math.round(opts.font * (w / 1200));
const band = (text, anchor) => {
  if (!text) return "";
  const lines = wrap(text, Math.round(30 * (w / 1200) + 14));
  const lineH = Math.round(font * 1.22);
  const pad = Math.round(font * 0.5);
  const boxH = lines.length * lineH + pad * 2;
  const y0 = anchor === "top" ? 0 : h - boxH;
  const tspans = lines
    .map((l, i) => `<tspan x="${w / 2}" dy="${i === 0 ? 0 : lineH}">${xml(l)}</tspan>`)
    .join("");
  const firstY = y0 + pad + font * 0.95;
  return `
  <rect x="0" y="${y0}" width="${w}" height="${boxH}" fill="#0d1117" opacity="0.82"/>
  <text x="${w / 2}" y="${firstY}" text-anchor="middle" font-family="Segoe UI, Helvetica, Arial, sans-serif"
        font-size="${font}" font-weight="700" fill="#ffffff" letter-spacing="0.5">${tspans}</text>`;
};

const overlay = Buffer.from(
  `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">${band(opts.top, "top")}${band(opts.bottom, "bottom")}</svg>`
);

const info = await sharp(baseBuf)
  .composite([{ input: overlay, top: 0, left: 0 }])
  .webp({ quality: 84, effort: 5 })
  .toFile(output);

console.log(JSON.stringify({ out: output, width: info.width, height: info.height, bytes: info.size }));
