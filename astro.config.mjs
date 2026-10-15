// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import { SITE } from './src/data/site.ts';

// `SITE.url` (src/data/site.ts) is the one place the production domain is
// defined: canonicals, sitemap, robots.txt, structured data and the RSS feed all
// derive from it. See docs/DEPLOY.md for the domain-change procedure.
export default defineConfig({
  site: SITE.url,
  trailingSlash: 'always',
  build: {
    // /about/ -> /about/index.html  (clean URLs on Cloudflare Pages / Vercel)
    format: 'directory',
  },
  integrations: [
    sitemap({
      // Utility pages should not be indexed.
      filter: (page) => !page.includes('/404') && !page.includes('/contact-thanks'),
    }),
  ],
});
