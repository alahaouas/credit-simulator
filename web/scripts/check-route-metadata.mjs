/* global process, console */
// ============================================================
// Guards the SEO baseline against the one failure mode that is silent.
//
// A 'use client' page cannot export `metadata` — Next ignores it with no error,
// no warning and no build failure. So a new route added without a server
// `layout.tsx` inherits the root layout's title AND its `alternates.canonical`
// of '/', and is crawlable by default. Nothing fails; it is only ever found in
// Search Console, weeks later.
//
// This check makes that loud. For every directory under app/ that holds a
// page.tsx, its top-level segment must appear in exactly one of PUBLIC_PATHS or
// PRIVATE_PATHS in lib/site.ts, and the segment's layout.tsx must carry the
// metadata that list implies.
//
//   npm run check:routes
//
// See docs/seo.md.
// ============================================================

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, relative } from 'node:path';

const WEB = join(dirname(fileURLToPath(import.meta.url)), '..');
const APP = join(WEB, 'app');
const SITE = join(WEB, 'lib', 'site.ts');

/**
 * Reads one `export const <name> = [...]` string array out of lib/site.ts.
 *
 * Regex rather than an import because the file is TypeScript and this script is
 * plain Node. It is narrow on purpose: a reformatted or renamed list makes it
 * throw rather than silently match nothing, which would turn this whole check
 * into a no-op that still reports success.
 */
function readPathList(source, name) {
  const match = source.match(new RegExp(`export const ${name}\\s*=\\s*\\[([^\\]]*)\\]`));
  if (!match) throw new Error(`could not find "export const ${name} = [...]" in lib/site.ts`);

  const paths = [...match[1].matchAll(/'([^']+)'/g)].map((m) => m[1]);
  if (paths.length === 0) throw new Error(`${name} in lib/site.ts parsed as empty`);
  return paths;
}

/** Every route that has a page, as a path: '/', '/simulate', '/share/[token]'. */
function routesWithPages(dir = APP, prefix = '') {
  const routes = [];
  const entries = readdirSync(dir);

  if (entries.includes('page.tsx')) routes.push(prefix === '' ? '/' : prefix);

  for (const entry of entries) {
    if (!statSync(join(dir, entry)).isDirectory()) continue;
    // Private folders (_name) hold no routes; route groups ((name)) hold routes
    // but contribute nothing to the URL.
    if (entry.startsWith('_')) continue;
    const segment = entry.startsWith('(') && entry.endsWith(')') ? '' : `/${entry}`;
    routes.push(...routesWithPages(join(dir, entry), prefix + segment));
  }
  return routes;
}

const source = readFileSync(SITE, 'utf-8');
const publicPaths = readPathList(source, 'PUBLIC_PATHS');
const privatePaths = readPathList(source, 'PRIVATE_PATHS');

const overlap = publicPaths.filter((path) => privatePaths.includes(path));
const errors = overlap.map(
  (path) => `${path} is in both PUBLIC_PATHS and PRIVATE_PATHS in lib/site.ts`
);

// robots.txt `Disallow` matches by prefix, so a private '/share' would also block
// a public '/shareholders' — silently, since the page would still build, render
// and sit in the sitemap while being uncrawlable. Cheaper to forbid the collision
// than to make the Disallow lines exact: several private paths ('/results',
// '/history') are real pages that a trailing slash would stop matching.
for (const publicPath of publicPaths) {
  for (const privatePath of privatePaths) {
    if (publicPath.startsWith(privatePath)) {
      errors.push(
        `public ${publicPath} starts with private ${privatePath}, so the robots.txt ` +
          `"Disallow: ${privatePath}" prefix would block it. Rename one of them.`
      );
    }
  }
}

for (const route of routesWithPages()) {
  // '/share/[token]' is governed by the '/share' segment: that is where the
  // layout lives and what robots.txt disallows.
  const segment = route === '/' ? '/' : `/${route.split('/')[1]}`;
  const isPublic = publicPaths.includes(segment);
  const isPrivate = privatePaths.includes(segment);

  if (!isPublic && !isPrivate) {
    errors.push(
      `${route} has a page but ${segment} is in neither PUBLIC_PATHS nor PRIVATE_PATHS ` +
        `in lib/site.ts. Add it to one: a route in neither is crawlable by default and ` +
        `inherits the root layout's title and canonical.`
    );
    continue;
  }

  // The root segment's metadata is the root layout's, which is read directly.
  const layout = segment === '/' ? join(APP, 'layout.tsx') : join(APP, segment, 'layout.tsx');

  let contents;
  try {
    contents = readFileSync(layout, 'utf-8');
  } catch {
    errors.push(
      `${route} has no server layout at ${relative(WEB, layout)}. A 'use client' page ` +
        `cannot export metadata, so without one this route has no title of its own.`
    );
    continue;
  }

  if (isPublic && !/alternates\s*:\s*{[^}]*canonical/.test(contents)) {
    errors.push(`${relative(WEB, layout)} is public but sets no alternates.canonical`);
  }
  if (isPrivate && !/index\s*:\s*false/.test(contents)) {
    errors.push(
      `${relative(WEB, layout)} is private but sets no robots.index: false. A redirect ` +
        `to sign-in is not a noindex — the URL still enters the index, as a soft 404.`
    );
  }
  // A private route inheriting the root canonical would point at '/' while also
  // asking not to be indexed.
  if (isPrivate && !/canonical\s*:\s*null/.test(contents)) {
    errors.push(
      `${relative(WEB, layout)} is private but does not clear the inherited canonical ` +
        `(alternates: { canonical: null })`
    );
  }
}

// lib/site.ts reads VERCEL_PROJECT_PRODUCTION_URL, which has no NEXT_PUBLIC_
// prefix and is therefore undefined in the browser. A 'use client' file that
// imported it would silently get the localhost fallback instead of the real
// origin — no error, no warning, wrong links. Keep the module server-only.
function sourceFiles(dir, found = []) {
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      if (entry !== 'node_modules' && !entry.startsWith('.')) sourceFiles(path, found);
    } else if (/\.tsx?$/.test(entry)) {
      found.push(path);
    }
  }
  return found;
}

for (const dir of ['app', 'components', 'hooks', 'lib']) {
  for (const file of sourceFiles(join(WEB, dir))) {
    const contents = readFileSync(file, 'utf-8');
    const isClient = /^\s*['"]use client['"]/m.test(contents);
    const importsSite = /from\s+['"]@\/lib\/site['"]/.test(contents);
    if (isClient && importsSite) {
      errors.push(
        `${relative(WEB, file)} is a 'use client' file importing @/lib/site. That module ` +
          `reads VERCEL_PROJECT_PRODUCTION_URL, which is undefined in the browser, so ` +
          `SITE_URL would silently fall back to localhost there. Pass the value in from a ` +
          `server component instead.`
      );
    }
  }
}

if (errors.length > 0) {
  console.error(`check:routes failed (${errors.length}):`);
  for (const error of errors) console.error(`  - ${error}`);
  process.exit(1);
}

console.log('check:routes: every route segment is classified and carries its metadata');
