import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

/**
 * Article collection.
 *
 * Publishing gate: `draft` defaults to TRUE, so a markdown file dropped into
 * src/content/articles/ is invisible until someone deliberately flips it to
 * false. That keeps the pre-publication review gate (representative sign-off)
 * enforced by the build itself rather than by discipline alone.
 */
const articles = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/articles' }),
  schema: z.object({
    title: z.string().max(120),
    description: z.string().min(50).max(200),
    category: z.enum([
      'start-a-business',
      'startup-costs',
      'licensing-and-registration',
      'pricing',
      'tools-and-software',
      'getting-customers',
    ]),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    author: z.string().default("The Owner's Handbook Editorial Team"),
    /** 1-3 primary sources (agency pages, vendor pricing) rendered as citations. */
    sources: z
      .array(z.object({ label: z.string(), url: z.string().url() }))
      .default([]),
    /** Internal links to other guides, by slug. Rendered as a "Related" block. */
    related: z.array(z.string()).default([]),
    heroImage: z.string().optional(),
    heroImageAlt: z.string().optional(),
    /** Flip to false only after editorial approval. */
    draft: z.boolean().default(true),
  }),
});

export const collections = { articles };
