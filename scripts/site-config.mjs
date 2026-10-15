/**
 * Reads the site identity out of `src/data/site.ts` — the single source of truth
 * for the domain, site name and contact address.
 *
 * Every script that needs to know "what is this site called / where does it
 * live" must come through here instead of hardcoding the domain, so that
 * renaming the site stays a one-place change.
 */
import { readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const SITE_FILE = join(repoRoot, 'src', 'data', 'site.ts');

/** The `export const SITE = { ... } as const;` block, without the wrapper. */
export const SITE_BLOCK_RE = /(export const SITE = \{)([\s\S]*?)(\n\} as const;)/;

const readField = (block, key) => {
  const match = block.match(
    new RegExp(`\\n\\s*${key}:\\s*("([^"]*)"|'([^']*)')`),
  );
  if (!match) {
    throw new Error(
      `src/data/site.ts: could not read SITE.${key} — did the file move or change shape?`,
    );
  }
  return match[2] ?? match[3];
};

export function readSite() {
  const raw = readFileSync(SITE_FILE, 'utf8');
  const block = raw.match(SITE_BLOCK_RE);
  if (!block) {
    throw new Error(
      'src/data/site.ts: could not find the `export const SITE = { ... } as const;` block',
    );
  }
  const [, prefix, body, suffix] = block;
  const url = readField(body, 'url').replace(/\/+$/, '');
  const domain = readField(body, 'domain');
  if (!url.endsWith(domain) && !/^https?:\/\/localhost/.test(url)) {
    throw new Error(
      `src/data/site.ts: SITE.url (${url}) does not end with SITE.domain (${domain}); fix before building`,
    );
  }
  return {
    raw,
    prefix,
    body,
    suffix,
    url,
    domain,
    name: readField(body, 'name'),
    shortName: readField(body, 'shortName'),
    publisher: readField(body, 'publisher'),
    contactEmail: readField(body, 'contactEmail'),
  };
}

/** Escape a literal string for use inside a RegExp. */
export const escapeRe = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
