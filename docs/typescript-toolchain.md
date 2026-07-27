# TypeScript toolchain (`web/`)

## Why two TypeScript packages are installed

`web/` installs **two** TypeScript packages on purpose:

| `package.json` entry | Role |
|---|---|
| `"typescript": "6.0.3"` | The JS compiler API. Consumed by `next build`, `typescript-eslint`, and `tsserver`/IDE. |
| `"typescript-native": "npm:typescript@7.0.2"` | The native (Go) compiler. Used only by `npm run typecheck`. |

`typescript-native` is an **npm alias** — the real `typescript@7.0.2` tarball resolved under a
name nothing else claims.

### Why TypeScript 7 cannot simply replace `typescript`

This is what [PR #180](https://github.com/alahaouas/credit-simulator/pull/180) (Dependabot,
`typescript` 6.0.3 → 7.0.2) runs into. That PR as written is **not mergeable**, and the reasons
are real:

- `typescript@7` ships **no JS compiler API** (`main` is `lib/version.cjs`; only `unstable/*`
  subpaths remain) and **no `tsserver` binary**.
- `typescript-eslint` caps its peer at `typescript >=4.8.4 <6.1.0` — every published tag,
  including `canary`. `npm ci` therefore fails with `ERESOLVE`.
- **Next.js type-checks inside `next build` using that same JS API.** Even setting the linter
  aside, `typescript@7` alone would break the build. This constraint is specific to this repo
  and does not apply to a Vite project.

What *is* wrong in the earlier review comments on #180 is the conclusion that nothing in the
repo could change that. Installing TS 7 under an alias sidesteps the peer bound entirely —
no `--legacy-peer-deps`, no peer override, and the linter still runs against exactly the
TypeScript version its peer range names.

## What this does and does not buy

Measured 2026-07-27 on `web/` (64 `.ts`/`.tsx` files), 3 runs each, identical invocation
(`node node_modules/<package>/bin/tsc --noEmit`), `tsconfig.tsbuildinfo` deleted before every
run, both compilers passing clean:

| Compiler | 3 runs | Mean |
|---|---|---|
| TypeScript 6.0.3 (JS) | 2.26 / 2.21 / 2.47 s | **2.31 s** |
| TypeScript 7.0.2 (native) | 0.37 / 0.36 / 0.35 s | **0.36 s** |

≈ **6.4×**, and no source change was needed — the codebase is TS 7 clean as-is.

**This does not make `next build` faster.** Next.js still runs its own type check through
TypeScript 6. The gain is a fast standalone gate: `npm run typecheck` fails in well under a
second locally, and the CI step placed before the build fails in seconds instead of after a
full Next build.

> Do not "optimise" this by setting `typescript.ignoreBuildErrors` in `next.config.mjs` to skip
> Next's check. `tsconfig.json` includes `.next/types/**/*.ts` — generated route types that only
> exist *after* a build. A standalone `tsc` run before the build silently skips them, so the two
> checks do not cover the same surface.

## Scripts

| Script | Compiler |
|---|---|
| `npm run typecheck` | TS 7 native — also the CI *Type check* step |
| `npm run typecheck:classic` | TS 6.0.3, to diff diagnostics if the two ever disagree |
| `npm run build` | `next build` — unchanged, still type-checks with TS 6 |

`node_modules/.bin/tsc` resolves to **6.0.3**; a hand-typed `npx tsc` does not silently switch
compilers. The native compiler is reachable only through the explicit script path.

## Both versions are pinned without a caret

`"typescript": "6.0.3"` — **exact, deliberate**. `^6.0.3` allows 6.1.0, which crosses
`typescript-eslint`'s `<6.1.0` peer bound and breaks lint on a plain `npm update`. Do not
restore the caret while this arrangement exists.

## Cleanup — when to collapse back to one package

**Trigger:** `npm view typescript-eslint peerDependencies.typescript` accepts `7.x`
*and* the installed Next.js major supports the TS 7 native compiler. Both are required.

**Steps:**

1. Remove `typescript-native`; set `"typescript"` to `7.x` (still caret-free).
2. Restore `"typecheck": "tsc --noEmit"`; drop `typecheck:classic`.
3. Bump `typescript` and `typescript-eslint` in the **same** PR so the lockfile changes once.
4. Delete this document and its reference in `CLAUDE.md`.
5. Verify `npm ci`, `npm run lint`, `npm run typecheck`, `npm run build` from a clean install.

Closing [PR #180](https://github.com/alahaouas/credit-simulator/pull/180) is not the same as
doing this — the upgrade is still wanted, and that PR should be refreshed by Dependabot once
the trigger conditions hold.
