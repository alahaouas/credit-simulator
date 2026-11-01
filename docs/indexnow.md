# IndexNow

Announces the sitemap's URLs to **Bing and Yandex** when they change. Google
does not participate in IndexNow, so none of this affects Google — for Google
the levers are the sitemap and Search Console, see [seo.md](seo.md).

Worth having because Bing now also feeds Copilot and ChatGPT search results.

## How it is wired

| Piece | Role |
|---|---|
| `web/public/<key>.txt` | Proves ownership. Served at the site root; IndexNow fetches it on every submission. |
| `scripts/indexnow.mjs` | Reads the **live** sitemap, builds the payload, POSTs it. |
| `.github/workflows/indexnow.yml` | Runs the script after a push to `main` that changed the sitemap's source, and on demand. |

### The key file is the single source of truth

IndexNow's ownership contract is that the file is *named* after the key and
*contains* that same key. The script exploits exactly that: it scans
`web/public/` for a file whose name matches `[A-Za-z0-9-]{8,128}.txt` **and**
whose contents repeat its own name. So the key lives in precisely one place, and
the committed key cannot drift from the submitted one.

**The key is not a secret.** It is published at the site root by design, so it
belongs in the repository rather than in a GitHub secret. A secret would create
a second source of truth that silently disagrees with the deployed file, and
buys nothing: anyone can read the key off the live site.

`web/public/` is served at the site root by the `web` service — the root
`vercel.json` rewrites `/(.*)` to it, and Next.js serves `public/` from `/`. So
the key file lands at `https://<domain>/<key>.txt`, which is where IndexNow
looks for it.

### Rotating the key

Replace `web/public/<old>.txt` with `web/public/<new>.txt`. No other file
mentions the key. Delete the old file in the same commit — two valid key files
make the script fail loudly rather than pick one at random.

## The site URL comes from a repository variable

This sitemap is generated, not committed, so the script has to fetch it — and to
fetch it, it needs the host. Set a GitHub Actions **repository variable** (not a
secret; the domain is public):

```
Settings → Secrets and variables → Actions → Variables → SITE_URL
```

to the same value as `NEXT_PUBLIC_SITE_URL` on Vercel. Locally, pass
`--host=https://<domain>` or export `SITE_URL`. The script rejects a non-https
URL, which is what an unset variable looks like.

If the two disagree, the script fails with `sitemap host is not …` rather than
submitting URLs for a host it cannot prove it owns.

## Triggers

`workflow_dispatch`, plus a push to `main` that touches `web/app/sitemap.ts`,
`web/lib/site.ts` (where `PUBLIC_PATHS` lives) or a `web/public/*.txt` key file.
This is deliberately narrower than the `paths-ignore` lists on the other
workflows: every submitted URL counts against the site's crawl quota, so
re-announcing the same four URLs on every deploy would spend quota to tell Bing
nothing new. Widening it is a regression, not a cleanup.

## Why `--wait`, and how it differs here

A push and its Vercel deploy race each other. Submitting immediately can
announce URLs while the previous build is still being served, and can hit the
key file before it is deployed — which IndexNow answers with a bare `403` for
every URL in the request.

A project with a committed `public/sitemap.xml` can wait until the live sitemap
matches the one in the commit. **That check is not possible here**: the sitemap
is produced by `web/app/sitemap.ts` at build time, so there is no committed copy
to compare against. The script checks readiness by consequence instead, which is
what actually matters — 20 attempts, 15 s apart, until all of:

- `https://<host>/<key>.txt` is reachable and contains the key;
- `https://<host>/sitemap.xml` answers 200 and lists at least one `<loc>`, all
  on the expected host;
- **every URL the sitemap lists answers 200** to a `HEAD` request.

The last one covers the freshness case the set comparison would have covered: a
page added in this commit 404s until its deploy is live, so the run waits. It
does not detect a page *removed* in this commit, which is harmless — a removed
URL is simply not in the live sitemap, so it is never submitted.

If readiness never settles the script exits non-zero rather than submit: a
failed job is recoverable, a wrong announcement is not.

## Running it by hand

```bash
node scripts/indexnow.mjs --dry-run --host=https://<domain>   # print host, key and URLs; send nothing
node scripts/indexnow.mjs --host=https://<domain>             # submit immediately
node scripts/indexnow.mjs --wait --host=https://<domain>      # wait for the deploy, then submit
```

`200` means accepted, `202` means accepted with key validation pending (normal
on first use). `403` means the key file was not reachable — it has to be
deployed before the first submission. `422` means a URL does not belong to the
declared host.

## What it does not do

- Nothing for Google.
- No guarantee of indexing: submission requests a crawl, it does not promise one.
- Removals are not handled. The script only ever submits what the live sitemap
  currently lists.
