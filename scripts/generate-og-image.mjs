/**
 * Generates public/og-default.png — the 1200x630 social share card used by
 * og:image / twitter:image and as the fallback `image` in Article structured data.
 *
 * Run with:  node scripts/generate-og-image.mjs
 *
 * It is dependency-free on purpose (zlib is in Node core) so the image can be
 * regenerated on any machine without installing an image library.
 */
import { deflateSync } from 'node:zlib';
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const WIDTH = 1200;
const HEIGHT = 630;

const NAVY = [0x12, 0x30, 0x4a];
const NAVY_DEEP = [0x0c, 0x23, 0x38];
const CREAM = [0xf4, 0xf1, 0xea];
const ACCENT = [0xc8, 0x76, 0x3c];
const WHITE = [0xff, 0xff, 0xff];

const pixels = new Uint8Array(WIDTH * HEIGHT * 3);

const setPixel = (x, y, [r, g, b]) => {
  if (x < 0 || y < 0 || x >= WIDTH || y >= HEIGHT) return;
  const i = (y * WIDTH + x) * 3;
  pixels[i] = r;
  pixels[i + 1] = g;
  pixels[i + 2] = b;
};

const fillRect = (x0, y0, x1, y1, color) => {
  for (let y = y0; y < y1; y += 1) {
    for (let x = x0; x < x1; x += 1) setPixel(x, y, color);
  }
};

// Background: deep navy with a subtle vertical gradient.
for (let y = 0; y < HEIGHT; y += 1) {
  const t = y / HEIGHT;
  const color = NAVY.map((c, i) => Math.round(c * (1 - t) + NAVY_DEEP[i] * t));
  fillRect(0, y, WIDTH, y + 1, color);
}

// The "handbook" motif: a cream page with an accent spine and text rules,
// mirroring the site favicon.
const pageX0 = 90;
const pageY0 = 120;
const pageX1 = 1110;
const pageY1 = 430;
fillRect(pageX0 + 10, pageY0 + 10, pageX1 + 10, pageY1 + 10, NAVY_DEEP); // shadow
fillRect(pageX0, pageY0, pageX1, pageY1, CREAM);
fillRect(pageX0, pageY0, pageX0 + 34, pageY1, ACCENT);

const rules = [820, 700, 760, 620, 480];
rules.forEach((width, index) => {
  const y = pageY0 + 48 + index * 44;
  const shade = index === 0 ? NAVY : NAVY.map((c) => Math.round(c * 1 + (255 - c) * (index * 0.14)));
  fillRect(pageX0 + 72, y, pageX0 + 72 + width, y + 20, shade);
});

// Under the page: a headline bar and a short accent underline.
fillRect(90, 480, 640, 512, WHITE);
fillRect(90, 540, 300, 554, ACCENT);
fillRect(330, 540, 470, 554, [0x2f, 0x4d, 0x69]);

// ---- PNG encoding -------------------------------------------------------

const crcTable = (() => {
  const table = new Int32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c;
  }
  return table;
})();

const crc32 = (buf) => {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i += 1) c = crcTable[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
};

const chunk = (type, data) => {
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length, 0);
  const typeAndData = Buffer.concat([Buffer.from(type, 'ascii'), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(typeAndData), 0);
  return Buffer.concat([length, typeAndData, crc]);
};

const ihdr = Buffer.alloc(13);
ihdr.writeUInt32BE(WIDTH, 0);
ihdr.writeUInt32BE(HEIGHT, 4);
ihdr[8] = 8; // bit depth
ihdr[9] = 2; // colour type: truecolour RGB
ihdr[10] = 0;
ihdr[11] = 0;
ihdr[12] = 0;

// Raw scanlines, each prefixed with filter type 0 (None).
const raw = Buffer.alloc(HEIGHT * (WIDTH * 3 + 1));
for (let y = 0; y < HEIGHT; y += 1) {
  const rowStart = y * (WIDTH * 3 + 1);
  raw[rowStart] = 0;
  Buffer.from(pixels.buffer, y * WIDTH * 3, WIDTH * 3).copy(raw, rowStart + 1);
}

const png = Buffer.concat([
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
  chunk('IHDR', ihdr),
  chunk('IDAT', deflateSync(raw, { level: 9 })),
  chunk('IEND', Buffer.alloc(0)),
]);

const outPath = resolve(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'og-default.png');
mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, png);
console.log(`Wrote ${outPath} (${WIDTH}x${HEIGHT}, ${png.length} bytes)`);
