// Print width/height/bytes for image files as JSON, using the same libvips build as
// the rest of the pipeline. Usage: node img_meta.mjs file1 [file2 ...]
import sharp from "sharp";

const files = process.argv.slice(2);
const out = [];
for (const f of files) {
  try {
    const meta = await sharp(f).metadata();
    const { size } = await import("node:fs/promises").then((fs) => fs.stat(f));
    out.push({ file: f, format: meta.format, width: meta.width, height: meta.height, bytes: size });
  } catch (err) {
    out.push({ file: f, error: String(err.message || err) });
  }
}
console.log(JSON.stringify(out));
