// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// The Owner's Handbook — canonical site URL is the production domain.
// Canonicals/sitemap/robots all derive from `site`, so this is the single
// place to change if the domain ever moves.
export default defineConfig({
  site: 'https://ownerhandbook.com',
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
