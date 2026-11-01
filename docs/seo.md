# SEO baseline

What is in place so the public pages can be found, and which pages are kept out
of search on purpose.

This baseline was written after a sibling project (GammePlay) was de-indexed by
Google in October 2026. Its root cause — a client-side redirect that showed
crawlers nothing but an onboarding screen — does **not** exist here: this is a
Next.js App Router app, the public pages render their own content, and the
homepage links to all of them. The two gaps that did apply are the per-page
metadata and the declared language, both covered below.

## Indexable pages

| Path | Title | Why it is public |
|---|---|---|
| `/` | Credit Simulator — mortgage and loan simulator | Entry point, links to every other public page |
| `/simulate` | Simulate a mortgage | The product itself; no account needed |
| `/rates` | Mortgage rates and lending limits by country | Reference data for eight markets, useful on its own |
| `/legal` | Legal notice | Required, and expected to be reachable |

The list lives once, in [`web/lib/site.ts`](../web/lib/site.ts) as
`PUBLIC_PATHS`, and is read by `web/app/sitemap.ts`. Adding a public page means
adding it there **and** giving its segment a server layout with metadata.

## Pages excluded from search

`robots: { index: false, follow: false }` in each segment's `layout.tsx`, and
`Disallow` in `robots.txt`:

| Path | Why |
|---|---|
| `/auth` | Sign-in; a magic-link flow must not be crawled |
| `/results` | Renders one simulation from session state — unbounded near-duplicates of one page |
| `/compare` | Needs a session, and is driven by `?ids=` — private *and* unbounded |
| `/history`, `/preferences`, `/settings`, `/alerts` | The signed-in user's own data |
| `/share/<token>` | Readable only by whoever holds the token; every token is a distinct URL for the same page |
| `/api/*` | The FastAPI service, including its OpenAPI docs. `robots.txt` only — it never reaches Next.js |

**A redirect to sign-in is not a `noindex`.** `/compare`, `/history`,
`/preferences`, `/settings` and `/alerts` all send a visitor without a session to
`/auth`, and a crawler records that as a *soft 404* against the original URL:
the URL is still in the index, as a known-bad one. Only the `robots` directive
keeps it out.

`/compare` is in this list although it looks like a feature page. It is listed
with the private routes because it reads saved simulations through
`supabase.auth.getSession()` and redirects when there is none.

## Per-page metadata and the `'use client'` trap

Every page under `web/app/` is a `'use client'` component, and **a client
component cannot export `metadata`**. Next ignores it: no error, no warning, no
build failure. Before this change all eleven pages inherited the root layout's
single title, which collapses them into one search result.

The fix is one small **server** `layout.tsx` per route segment that exports
`metadata` and returns `children`. The page itself stays a client component and
is not touched. The root layout sets `metadataBase` and a title `template`, so
each segment only writes its own title and description.

If a new page needs a title, add the segment layout — do not try to export
`metadata` from the page.

### The guard

`npm run check:routes` (`web/scripts/check-route-metadata.mjs`, run in CI before
the type check) makes that failure loud. For every directory under `web/app/`
holding a `page.tsx` it requires:

- its top-level segment to be in `PUBLIC_PATHS` or `PRIVATE_PATHS`, not both;
- a `layout.tsx` for that segment;
- `alternates.canonical` on a public one;
- `robots.index: false` **and** `alternates: { canonical: null }` on a private
  one — without the second, the page inherits the root layout's canonical of
  `/` while also asking not to be indexed.

It was verified by adding a throwaway route and confirming each case fails, not
only by watching it pass.

## `NEXT_PUBLIC_SITE_URL` (required)

`metadataBase`, every `alternates.canonical`, `robots.txt` and the sitemap are
all built from it. It must be set on Vercel as a **Config** variable (not a
Secret — Vercel refuses a `NEXT_PUBLIC_` secret, and the value is public
anyway), to the site's own origin with no trailing slash:

```
NEXT_PUBLIC_SITE_URL=https://<the production domain>
```

A value that is not an absolute URL — `example.com`, with no scheme, which is
the easy mistake to make in the Vercel dashboard — fails the build with a message
naming the variable. That is deliberate: shipping canonicals that point nowhere
is worse than a failed deploy. An empty value is treated as unset.

Unset, the app falls back to `http://localhost:3000`. That fallback is
deliberately wrong-looking: a plausible production guess would publish
canonicals and a sitemap pointing at a domain nobody owns, which is harder to
notice and worse than a localhost URL that fails review at a glance. Check
`/robots.txt` on the deployed site after setting it.

## IndexNow

Bing and Yandex are notified when the sitemap's source changes. See
[indexnow.md](indexnow.md). Google does not take part in IndexNow; for Google
the levers are the sitemap and Search Console.

## Follow-up: locale-routed URLs

The UI switches between English and French from `localStorage`
(`web/lib/i18n.tsx`), so **both languages share one URL**. Consequences:

- The server can only render one `lang` attribute. It renders `lang="en"`, and
  the provider corrects `document.documentElement.lang` once the locale is
  known. That fixes assistive tech and a crawler that executes JavaScript, but
  the HTML a crawler receives still says English.
- Neither language can rank for the other's queries. There is no French URL for
  Google to index, so a search for *simulateur de prêt hypothécaire* has nothing
  to match even though the French page exists.
- No `hreflang` is possible, because `hreflang` needs one URL per language.

The real fix is locale-routed URLs — `/fr/simulate` beside `/simulate` — with
`generateMetadata` per locale, `alternates.languages`, both locales in the
sitemap, and the locale read from the path instead of `localStorage`. That is a
routing change across every page plus the e2e specs, which is why it was left
out of this baseline. Until it is done, French traffic will only ever arrive via
the English URLs.

## Verifying

After a deploy:

- `/robots.txt` lists the real domain and every disallowed path.
- `/sitemap.xml` lists exactly the four public URLs, on the real domain.
- `view-source:` on `/simulate` shows that page's own `<title>` and
  `<meta name="description">`, and a `<link rel="canonical">`.
- `view-source:` on `/results` shows `<meta name="robots" content="noindex, nofollow">`.
- Submit the sitemap in Search Console.

A preview deployment is behind Vercel Authentication by default, so none of the
above can be checked on one: every URL redirects to the auth wall. Check on the
production domain.

**Search Console's "Couldn't fetch" goes stale.** Measured on GammePlay: once a
sitemap fetch fails, Search Console keeps showing the failure and never retries
on its own, however healthy the sitemap is. The fix is to remove the sitemap and
submit it again — not to wait.
