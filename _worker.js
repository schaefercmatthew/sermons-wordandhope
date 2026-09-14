const ARTICLE_SLUGS = new Set(__ARTICLE_SLUGS__);

const TOP_LEVEL_FILES = new Set(["/robots.txt", "/sitemap.xml", "/articles-data.json", "/article-template.html", "/_headers", "/_redirects"]);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (path.startsWith('/articles/') || path === '/' || TOP_LEVEL_FILES.has(path)) {
      return env.ASSETS.fetch(request);
    }

    let slug = null;
    if (path.endsWith('.html')) {
      slug = path.slice(1, -5);
    } else if (!path.includes('.')) {
      slug = path.slice(1);
    }

    if (slug && ARTICLE_SLUGS.has(slug)) {
      const target = new URL(request.url);
      target.pathname = '/articles/' + slug + '.html';
      return env.ASSETS.fetch(target.toString());
    }

    return new Response('Not Found', { status: 404, headers: { 'Content-Type': 'text/plain' } });
  }
}
