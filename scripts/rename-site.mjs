#!/usr/bin/env node
/**
 * Rename / re-domain the site in one command.
 *
 *   npm run rename -- --name "Owner Handbook" --domain newdomain.example
 *
 * The domain lives in exactly one place (`SITE` in src/data/site.ts), so this
 * script only has to keep the few identity-adjacent strings in step: the SITE
 * block, the npm package slug, and the prose in README/docs that names the
 * production domain. It then tells you to build + verify, which asserts the
 * canonical host on every generated page.
 *
 * Options:
 *   --name    <string>  Site name (e.g. "The Owner's Handbook")
 *   --domain  <domain>  Apex domain without scheme (e.g. newdomain.example)
 *   --short   <string>  Short name used in nav/OG (default: keep current)
 *   --email   <string>  Contact address (default: hello@<domain>)
 *   --publisher <string> Schema publisher name (default: --name)
 *   --slug    <string>  npm package / GitHub repo slug (default: first label of --domain)
 *   --no-docs           Leave README.md / docs/*.md prose untouched
 *   --dry-run           Print the planned changes without writing
 */
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { readSite, repoRoot, SITE_FILE, SITE_BLOCK_RE } from './site-config.mjs';

const argv = process.argv.slice(2);
const opts = {};
for (let i = 0; i < argv.length; i += 1) {
  const arg = argv[i];
  if (!arg.startsWith('--')) continue;
  const key = arg.slice(2);
  if (key === 'no-docs' || key === 'dry-run') {
    opts[key] = true;
  } else {
    opts[key] = argv[++i];
  }
}

const fail = (message) => {
  console.error(`rename-site: ${message}`);
  process.exit(1);
};

const site = readSite();
const oldSlug = JSON.parse(readFileSync(join(repoRoot, 'package.json'), 'utf8')).name;

const domain = opts.domain;
if (!domain) fail('--domain is required (e.g. --domain newdomain.example)');
if (!/^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$/i.test(domain)) {
  fail(`"${domain}" is not a bare apex domain (no scheme, no path, no trailing dot)`);
}
const name = opts.name ?? site.name;
if (!name || name.length < 3) fail('--name must be at least 3 characters');

const next = {
  name,
  shortName: opts.short ?? site.shortName,
  domain,
  url: `https://${domain}`,
  publisher: opts.publisher ?? name,
  contactEmail: opts.email ?? `hello@${domain}`,
};
const slug = opts.slug ?? domain.split('.')[0].replace(/[^a-z0-9-]/gi, '-').toLowerCase();

if (next.name === site.name && next.domain === site.domain && slug === oldSlug) {
  console.log('rename-site: nothing to do — name, domain and slug are already set.');
  process.exit(0);
}

const changes = [];
const setField = (body, key, value) => {
  const re = new RegExp(`(\\n(\\s*)${key}:\\s*)("([^"]*)"|'([^']*)')`);
  if (!re.test(body)) fail(`src/data/site.ts: could not find SITE.${key}`);
  return body.replace(re, (_m, head, _indent, _all, doubleQuoted) => {
    const quote = doubleQuoted !== undefined ? '"' : "'";
    const escaped = String(value).replace(new RegExp(quote, 'g'), `\\${quote}`);
    return `${head}${quote}${escaped}${quote}`;
  });
};

// ---- 1. the SITE block ----------------------------------------------------
let body = site.body;
for (const key of ['name', 'shortName', 'domain', 'url', 'publisher', 'contactEmail']) {
  const before = body;
  body = setField(body, key, next[key]);
  if (before !== body) changes.push(`src/data/site.ts  SITE.${key} -> ${next[key]}`);
}
// Prose inside the SITE block (description/tagline) may name the site too, so
// carry the old name over to the new one there as well. Only double quotes are
// escaped: a new name containing an apostrophe belongs in a double-quoted field.
if (site.name !== next.name && body.includes(site.name)) {
  const mentions = body.split(site.name).length - 1;
  body = body.replaceAll(site.name, next.name.replace(/"/g, '\\"'));
  changes.push(`src/data/site.ts  ${mentions} in-prose mention(s) of the old name updated`);
}

const siteSource = site.raw.replace(SITE_BLOCK_RE, `${site.prefix}${body}${site.suffix}`);
if (!SITE_BLOCK_RE.test(site.raw)) fail('could not rewrite the SITE block');
// ---- 2. package slug ------------------------------------------------------
const packageFiles = ['package.json', 'package-lock.json'];
const packageWrites = [];
for (const file of packageFiles) {
  const path = join(repoRoot, file);
  if (!existsSync(path)) continue;
  const before = readFileSync(path, 'utf8');
  // The lockfile repeats the slug inside packages[""], so replace every exact hit.
  const after = before.replaceAll(`"name": "${oldSlug}"`, `"name": "${slug}"`);
  if (after !== before) {
    packageWrites.push([path, after]);
    changes.push(`${file}  name -> ${slug}`);
  }
}

// ---- 3. docs prose --------------------------------------------------------
const docWrites = [];
if (!opts['no-docs']) {
  const docFiles = [
    'README.md',
    join('docs', 'DEPLOY.md'),
    join('docs', 'SEO.md'),
  ].filter((file) => existsSync(join(repoRoot, file)));
  for (const file of docFiles) {
    const path = join(repoRoot, file);
    const before = readFileSync(path, 'utf8');
    const after = before
      .replaceAll(site.url, next.url)
      .replaceAll(site.domain, next.domain)
      .replaceAll(site.name, next.name);
    if (after !== before) {
      docWrites.push([path, after]);
      changes.push(`${file}  prose domain/name updated`);
    }
  }
}

if (changes.length === 0) {
  console.log('rename-site: no writable changes detected (check --help usage).');
  process.exit(0);
}

console.log(`rename-site: ${site.name} (${site.domain}) -> ${next.name} (${next.domain})`);
for (const change of changes) console.log(`  ${change}`);

if (opts['dry-run']) {
  console.log('\ndry-run: nothing written.');
  process.exit(0);
}

writeFileSync(SITE_FILE, siteSource);
for (const [path, content] of [...packageWrites, ...docWrites]) writeFileSync(path, content);

console.log(`
Next:
  1. npm run build && npm run verify     # verify asserts the canonical host on every page
  2. npm ci                              # refresh the lockfile against the new package name
  3. git add -A && git commit -m "Rename site to ${next.name} (${next.domain})"
  4. GitHub repo / Cloudflare Pages project / Search Console property: rename or add the
     new domain there, and keep the old one redirecting. See docs/DEPLOY.md.`);
