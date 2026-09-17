// Cloudflare Pages Function: catch-all for every request path.
//
// The site's _redirects file rewrites any top-level path like /some-slug
// or /some-slug.html to /articles/some-slug.html with a 200 status,
// unconditionally -- it has no way to check whether that article actually
// exists. That meant a bad or mistyped link (e.g. /this-does-not-exist)
// was silently rewritten to a missing file and Cloudflare's SPA-style
// fallback served the homepage with a 200 instead of a real 404.
//
// This Function runs before _redirects and does the existence check
// _redirects can't: known top-level files, /chat, /articles/*, /tools/*,
// and /api/* (handled by its own Function) are passed straight through
// to static asset resolution. A bare, extensionless path is checked
// against the real list of published article slugs; only a genuine
// match is passed through (letting _redirects do its normal rewrite to
// /articles/:slug.html). Anything else -- a bad slug, a bad .html link,
// any other unknown path -- gets the site's styled 404.html back with a
// real 404 status.

import ARTICLE_SLUGS from "../articles-data.json";

const SLUGS = new Set(ARTICLE_SLUGS.articles.map((a) => a.slug));

const PASSTHROUGH_PREFIXES = ["/articles/", "/tools/", "/api/", "/assets/"];
const PASSTHROUGH_EXACT = new Set([
  "/",
  "/chat",
  "/robots.txt",
  "/sitemap.xml",
  "/articles-data.json",
  "/article-template.html",
  "/404.html",
  "/_headers",
  "/_redirects",
  "/favicon.ico",
]);

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const path = url.pathname;

  if (
    PASSTHROUGH_EXACT.has(path) ||
    PASSTHROUGH_PREFIXES.some((prefix) => path.startsWith(prefix))
  ) {
    return env.ASSETS.fetch(request);
  }

  // A bare top-level slug, with or without .html -- the only shape the
  // article catch-all rules in _redirects rewrite.
  const slugMatch = path.match(/^\/([^/]+?)(\.html)?$/);
  const slug = slugMatch ? slugMatch[1] : null;

  if (slug && SLUGS.has(slug)) {
    return env.ASSETS.fetch(request);
  }

  const notFoundUrl = new URL("/404.html", request.url);
  const page = await env.ASSETS.fetch(notFoundUrl);
  return new Response(page.body, {
    status: 404,
    headers: page.headers,
  });
}
