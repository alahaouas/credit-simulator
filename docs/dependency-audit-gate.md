# Dependency audit gate

The `Web — lint + typecheck + build` job runs, before lint:

```
npm audit --audit-level=high
```

**Dev-inclusive on purpose.** `--omit=dev` is the usual form and it is the wrong one:
a dev-only advisory still ships in whatever the repo builds, and omitting them is how
a tree with high-severity findings reads as clean. On another repository a gate scoped
that way reported `0` while the tree carried 8 highs.

**Blocking at `high`, not `moderate`.** A dev-inclusive gate goes red when a new CVE
lands against a tool like `eslint` or `playwright`, through no fault of the PR in front
of it. High-severity advisories are worth stopping unrelated work for; moderates are
not. Moderates still appear in the job's output — read it rather than relying on the
exit code.

## Baseline

The gate went in from a measured **0 vulnerabilities, dev-inclusive** (2026-09-10). That
matters: a gate added on a red tree only ratifies whatever is already there. Because the
baseline was clean, a red run means the change under review reintroduced something.

Getting to that baseline took two fixes:

| Advisory | Fix |
|---|---|
| `sharp <= 0.35.4-rc.0` — libvips and libheif CVEs, high | Dependabot #237, `0.34.5 → 0.35.4` |
| `postcss <= 8.5.22` — path traversal via `sourceMappingURL`, high | Pinned `8.5.28` in `devDependencies` **and** `overrides` |

## The postcss pin is exact, and must stay exact

`web/package.json` carried `"overrides": {"postcss": "^8.5.10"}`. The caret is the whole
problem: the advisory's vulnerable range grew over time to `<= 8.5.22`, the caret range
still satisfied it, and the override went on resolving to a vulnerable `8.5.14` while
looking deliberate. An override is a security decision written as a version range — it
rots silently when the range moves under it.

So it is pinned exactly, in both places, and `npm audit` is what will now notice if it
rots again. Do not "tidy" it back to a caret.

Dependabot does not manage `overrides` at all, so no merge policy — auto or manual —
would have caught this. The audit gate is the only thing that does.

## When the gate goes red

**Do not run `npm audit fix`.** It can add more advisories than it removes and npm does
not say so; it is blocked by a hook on this workstation for that reason. `--force`
applies major downgrades.

Instead:

1. Baseline the counts: `npm audit --json` → `metadata.vulnerabilities`.
2. Pin or override the offending package to a version outside the advisory's range,
   checking the range itself rather than trusting `fixAvailable`.
3. Re-count and compare. A fix that raises the total is not a fix.

`npm audit --package-lock-only` works without `node_modules`, which is useful in a fresh
worktree.

## Related

`.github/workflows/ci.yml` has no `paths-ignore` on `pull_request`, and the `changes`
job exists, because these jobs are required status checks — see
[docs/required-status-checks.md](required-status-checks.md).
