import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { SITE } from '../data/site';
import { getPublishedArticles, categoryOf } from '../utils/articles';

export async function GET(context: APIContext) {
  const articles = await getPublishedArticles();

  return rss({
    title: SITE.name,
    description: SITE.description,
    site: context.site ?? SITE.url,
    items: articles.map((entry) => ({
      title: entry.data.title,
      description: entry.data.description,
      pubDate: entry.data.pubDate,
      link: `/articles/${entry.id}/`,
      categories: [categoryOf(entry).name],
    })),
    customData: `<language>${SITE.locale}</language>`,
  });
}
