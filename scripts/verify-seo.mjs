/**
 * Post-build SEO verification. Run after `npm run build`:
 *   node scripts/verify-seo.mjs
 *
 * Checks the generated dist/ output for the things that silently break SEO:
 * missing/duplicate canonicals, missing descriptions, multiple H1s, invalid
 * JSON-LD, internal links that 404, pages leaking out of the draft gate, and
 * sitemap entries that should not be there.
 */
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { readSite, escapeRe } from './site-config.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const dist = join(root, 'dist');

// The expected origin comes from src/data/site.ts, the single source of truth —
// never from a literal in this file. A half-finished rename therefore fails the
// checks below instead of shipping a mismatched canonical host.
const site = readSite();
const ORIGIN = site.url;

if (!existsSync(dist)) {
  console.error('dist/ not found — run `npm run build` first.');
  process.exit(1);
}

const walk = (dir) =>
  readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    return statSync(full).isDirectory() ? walk(full) : [full];
  });

const files = walk(dist);
const htmlFiles = files.filter((f) => f.endsWith('.html'));
const errors = [];
const warnings = [];

const pagePathFor = (file) => {
  const rel = relative(dist, file).split('\\').join('/');
  if (rel === 'index.html') return '/';
  if (rel.endsWith('/index.html')) return '/' + rel.slice(0, -'index.html'.length);
  // Astro emits a trailing-slash pathname for extension-less routes such as /404.
  return '/' + rel.replace(/\.html$/, '') + '/';
};

const pages = new Map(htmlFiles.map((f) => [pagePathFor(f), f]));

// ---- 0. single source of truth: no other file may hardcode the domain -----

// Renaming the site must stay a one-place change. Anything under src/ (except
// site.ts itself), astro.config.mjs and scripts/ that spells out the domain is
// one more edit waiting to be forgotten, so fail before that ships.
const singleSourceFiles = [
  ...walk(join(root, 'src')),
  join(root, 'astro.config.mjs'),
  ...walk(join(root, 'scripts')),
].filter(
  (file) =>
    file !== join(root, 'src', 'data', 'site.ts') &&
    /\.(ts|tsx|astro|js|mjs|json|md)$/.test(file),
);

for (const file of singleSourceFiles) {
  if (readFileSync(file, 'utf8').includes(site.domain)) {
    errors.push(
      `${relative(root, file).split('\\').join('/')}: hardcodes "${site.domain}" — reference SITE from src/data/site.ts instead`,
    );
  }
}

// ---- 1. per-page head/link/schema checks ---------------------------------

const internalLinks = new Set();

for (const [path, file] of pages) {
  const html = readFileSync(file, 'utf8');
  const label = path;

  const canonicals = [...html.matchAll(/<link rel="canonical" href="([^"]+)"/g)].map((m) => m[1]);
  if (canonicals.length !== 1) {
    errors.push(`${label}: expected exactly 1 canonical, found ${canonicals.length}`);
  } else {
    const expected = `${ORIGIN}${path}`;
    if (canonicals[0] !== expected) {
      errors.push(`${label}: canonical ${canonicals[0]} != ${expected}`);
    }
  }

  if (!/<meta name="description" content="[^"]{50,}"/.test(html)) {
    errors.push(`${label}: missing or too-short meta description`);
  }

  const h1s = [...html.matchAll(/<h1[\s>]/g)].length;
  if (h1s !== 1) errors.push(`${label}: expected 1 <h1>, found ${h1s}`);

  const title = html.match(/<title>([^<]*)<\/title>/);
  if (!title || title[1].trim().length < 10) errors.push(`${label}: missing/too-short <title>`);

  if (!new RegExp(`<meta property="og:image" content="${escapeRe(ORIGIN)}/`).test(html)) {
    errors.push(`${label}: og:image missing or not absolute`);
  }

  const ldBlocks = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)];
  if (ldBlocks.length === 0) errors.push(`${label}: no JSON-LD`);
  for (const [, raw] of ldBlocks) {
    try {
      const parsed = JSON.parse(raw);
      if (!parsed['@context'] || !parsed['@type']) {
        errors.push(`${label}: JSON-LD block without @context/@type`);
      }
    } catch (error) {
      errors.push(`${label}: invalid JSON-LD (${error.message})`);
    }
  }

  if (!/@type":"(Organization|WebSite)"/.test(html)) {
    errors.push(`${label}: Organization/WebSite entity block missing`);
  }

  for (const [, href] of html.matchAll(/href="(\/[^"#?]*)"/g)) {
    internalLinks.add(href);
  }
}

// ---- 2. draft gate: nothing unpublished may reach dist --------------------

// Draft guides must not appear as pages, links or feed items. Titles of *planned*
// guides are allowed to appear in a category's "in production" list, so check for
// the draft's route rather than its title.
const draftMarkers = ['/articles/example-guide/'];
for (const [path, file] of pages) {
  const html = readFileSync(file, 'utf8');
  for (const marker of draftMarkers) {
    if (html.includes(marker)) {
      errors.push(`${path}: draft article leaked into the build (${marker})`);
    }
  }
}
if (files.some((f) => f.includes('example-guide'))) {
  errors.push('a draft article was emitted into dist/');
}
if (existsSync(join(dist, 'rss.xml')) && readFileSync(join(dist, 'rss.xml'), 'utf8').includes('example-guide')) {
  errors.push('draft article present in the RSS feed');
}

// ---- 3. internal links resolve -------------------------------------------

const resolves = (href) => {
  const clean = href.split('#')[0].split('?')[0];
  if (clean.endsWith('/')) return pages.has(clean);
  if (/\.(xml|txt|png|svg|ico|css|js|webp|jpg)$/.test(clean)) {
    return existsSync(join(dist, clean.slice(1)));
  }
  return pages.has(clean + '/') || pages.has(clean);
};

for (const href of [...internalLinks].sort()) {
  if (href.startsWith('/_astro/')) continue;
  if (!resolves(href)) errors.push(`broken internal link: ${href}`);
}

// ---- 4. sitemap + robots -------------------------------------------------

const sitemapIndex = join(dist, 'sitemap-index.xml');
if (!existsSync(sitemapIndex)) {
  errors.push('sitemap-index.xml missing');
} else {
  const sitemapFiles = files.filter((f) => /sitemap-\d+\.xml$/.test(f));
  const sitemapLocs = sitemapFiles
    .flatMap((f) => [...readFileSync(f, 'utf8').matchAll(/<loc>([^<]+)<\/loc>/g)])
    .map((m) => m[1]);

  for (const loc of sitemapLocs) {
    if (!loc.startsWith(ORIGIN)) errors.push(`sitemap: non-canonical host ${loc}`);
  }
  if (sitemapLocs.some((loc) => loc.includes('/404'))) {
    errors.push('sitemap contains /404/ (should be filtered)');
  }
  // Every indexable page must be in the sitemap.
  for (const [path, file] of pages) {
    const html = readFileSync(file, 'utf8');
    const noindex = /<meta name="robots" content="noindex/.test(html);
    const url = `${ORIGIN}${path}`;
    if (!noindex && path !== '/rss.xml' && !sitemapLocs.includes(url)) {
      warnings.push(`not in sitemap: ${url}`);
    }
  }
  console.log(`sitemap: ${sitemapLocs.length} URLs`);
}

const robots = join(dist, 'robots.txt');
if (!existsSync(robots)) {
  errors.push('robots.txt missing from dist');
} else {
  const text = readFileSync(robots, 'utf8');
  if (!text.includes(`Sitemap: ${ORIGIN}/sitemap-index.xml`)) {
    errors.push('robots.txt: sitemap line missing');
  }
  if (!text.includes('Mediapartners-Google')) {
    warnings.push('robots.txt: AdSense crawler block missing');
  }
}

// ---- report --------------------------------------------------------------

console.log(`pages checked: ${pages.size}`);
for (const path of [...pages.keys()].sort()) console.log(`  ${path}`);
if (warnings.length) {
  console.log(`\n${warnings.length} warning(s):`);
  for (const w of warnings) console.log(`  ! ${w}`);
}
if (errors.length) {
  console.log(`\n${errors.length} ERROR(S):`);
  for (const e of errors) console.log(`  x ${e}`);
  process.exit(1);
}
console.log('\nAll SEO checks passed.');
