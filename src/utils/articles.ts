import { getCollection, type CollectionEntry } from 'astro:content';
import { CATEGORIES, type Category, type CategorySlug } from '../data/site';

export type Article = CollectionEntry<'articles'>;

/**
 * Production builds only include articles with `draft: false`.
 * In `astro dev` every file is visible so writers can preview before approval —
 * the review gate is enforced at build time, not by convention.
 */
export function isPublished(entry: Article): boolean {
  return import.meta.env.PROD ? entry.data.draft !== true : true;
}

export async function getPublishedArticles(): Promise<Article[]> {
  const entries = await getCollection('articles', isPublished);
  return entries.sort(
    (a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf(),
  );
}

export async function getArticlesByCategory(
  slug: CategorySlug,
): Promise<Article[]> {
  const entries = await getPublishedArticles();
  return entries.filter((entry) => entry.data.category === slug);
}

export function categoryOf(entry: Article): Category {
  const category = CATEGORIES.find((c) => c.slug === entry.data.category);
  if (!category) {
    throw new Error(
      `Article "${entry.id}" references unknown category "${entry.data.category}".`,
    );
  }
  return category;
}

export function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    timeZone: 'UTC',
  });
}

/** Reading order for related-article lists: newest first, no self-references. */
export function relatedArticles(
  current: Article,
  all: Article[],
  limit = 3,
): Article[] {
  const bySlug = new Map(all.map((entry) => [entry.id, entry]));
  const explicit = current.data.related
    .map((slug) => bySlug.get(slug))
    .filter((entry): entry is Article => Boolean(entry));

  if (explicit.length >= limit) return explicit.slice(0, limit);

  const sameCategory = all.filter(
    (entry) =>
      entry.id !== current.id &&
      entry.data.category === current.data.category &&
      !explicit.some((e) => e.id === entry.id),
  );

  return [...explicit, ...sameCategory].slice(0, limit);
}
