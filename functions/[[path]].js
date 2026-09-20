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
// _redirects can't: known top-level files, /articles/*, /tools/*, and
// /api/* (handled by its own Function) are passed straight through to
// static asset resolution. /chat and bare article slugs are rewritten
// to their literal asset path. Fetching any .html path through
// ASSETS.fetch triggers Cloudflare's own extensionless-URL redirect
// (e.g. /articles/psalm-29.html -> 308 -> /articles/psalm-29), which
// would turn the old invisible _redirects rewrite into a visible
// redirect the client can see -- so fetchAsset follows that one hop
// internally and returns the final content directly. A bare,
// extensionless path is checked against the real list of published
// article slugs; only a genuine match is rewritten through. Anything
// else -- a bad slug, a bad .html link, any other unknown path -- gets
// the site's styled 404.html back with a real 404 status.
//
// Root-level files (depth-1 paths like /sitemap.xml or /robots.txt) can't
// be reached through env.ASSETS.fetch() from inside this catch-all Function
// -- Cloudflare's static asset resolution 404s on them even though the
// files exist in the deploy output and are served fine at any deeper path
// (e.g. /articles/*). Rather than depend on that, ROOT_FILES below answers
// those two paths directly from content mirrored at build time from the
// repo's root robots.txt/sitemap.xml, bypassing ASSETS.fetch entirely.

import ARTICLE_SLUGS from "../articles-data.json";
import { ROOT_FILES } from "./_root-files.js";

const SLUGS = new Set(ARTICLE_SLUGS.articles.map((a) => a.slug));

const PASSTHROUGH_PREFIXES = ["/articles/", "/tools/", "/api/", "/assets/"];
const PASSTHROUGH_EXACT = new Set([
  "/",
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

  if (Object.hasOwn(ROOT_FILES, path)) {
    const file = ROOT_FILES[path];
    return new Response(file.body, {
      status: 200,
      headers: { "content-type": file.contentType },
    });
  }

  if (path === "/chat") {
    return fetchAsset(env, request, "/tools/chat.html");
  }

  if (path.startsWith("/api/")) {
    return env.ASSETS.fetch(request);
  }

  if (
    PASSTHROUGH_EXACT.has(path) ||
    PASSTHROUGH_PREFIXES.some((prefix) => path.startsWith(prefix))
  ) {
    return fetchAsset(env, request, path);
  }

  // A bare top-level slug, with or without .html -- the only shape the
  // article catch-all rules in _redirects rewrite.
  const slugMatch = path.match(/^\/([^/]+?)(\.html)?$/);
  const slug = slugMatch ? slugMatch[1] : null;

  if (slug && SLUGS.has(slug)) {
    return fetchAsset(env, request, `/articles/${slug}.html`);
  }

  const page = await fetchAsset(env, request, "/404.html");
  return new Response(page.body, {
    status: 404,
    headers: page.headers,
  });
}

// Fetches assetPath through the ASSETS binding, following one internal
// redirect hop (Cloudflare's extensionless-URL normalization for .html
// paths) so the client sees the final content directly, never the hop.
async function fetchAsset(env, request, assetPath) {
  const target = new URL(assetPath, request.url);
  const first = await env.ASSETS.fetch(new Request(target.toString(), request));
  if (first.status >= 300 && first.status < 400 && first.headers.has("location")) {
    const redirected = new URL(first.headers.get("location"), request.url);
    return env.ASSETS.fetch(new Request(redirected.toString(), request));
  }
  return first;
}
