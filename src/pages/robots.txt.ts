import type { APIContext } from 'astro';
import { SITE } from '../data/site';

/**
 * robots.txt is generated from SITE.url rather than kept as a static file in
 * public/, so the sitemap line can never point at a stale host if the domain
 * changes (see docs/DEPLOY.md — "Changing the domain or site name").
 */
export function GET(context: APIContext) {
  const origin = (context.site ?? SITE.url).toString().replace(/\/$/, '');

  const body = `# robots.txt — ${SITE.name} (${origin})
# Only published, editorially approved content is exposed to crawlers.
# Draft articles are never built into the site, so nothing private is reachable.

User-agent: *
Allow: /
Disallow: /404/

# AdSense crawler needs access to serve and audit ads.
User-agent: Mediapartners-Google
Allow: /

User-agent: AdsBot-Google
Allow: /

Sitemap: ${origin}/sitemap-index.xml
`;

  return new Response(body, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}
