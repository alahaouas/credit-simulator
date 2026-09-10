# Required status checks on `main`

`main` carries a branch protection rule. As of 2026-09-10 these contexts are required:

- `Detect code changes`
- `Python — ruff + pytest`
- `Web — lint + typecheck + build`
- `Web — Playwright E2E`

CodeQL is deliberately **not** required — see below.

## Why `paths-ignore` had to go from the `pull_request` trigger

A workflow filtered out by `paths-ignore` does not run at all. Its checks therefore never
report, and GitHub treats a required check that never reports as *pending*, not as
passed. A docs-only PR would have sat unmergeable forever.

The saving is kept, just moved: `ci.yml` now always starts on a pull request, and a
`changes` job diffs the PR against its base and sets `code=true/false` using the same
path list that `paths-ignore` used. The three expensive jobs carry
`if: needs.changes.outputs.code == 'true'`, so a documentation-only PR skips them in
seconds.

**A skipped job satisfies a required check; an absent one does not.** That distinction is
the entire reason for the refactor, and it is why the fix could not simply be "require
fewer checks".

The `push` trigger keeps its `paths-ignore` — nothing gates on those runs.

## Why CodeQL is not required

`codeql.yml` still has `paths-ignore`, and its header explains why: advanced setup exists
precisely so a docs-only PR does not pay for a full multi-language analysis. Requiring it
would reintroduce the unmergeable-docs-PR problem for the sake of a check that already
runs on every code change. It stays advisory.

## Auto-merge

With required checks in place, GitHub's native auto-merge becomes safe: `gh pr merge --auto`
now waits for these contexts instead of merging immediately. `allow_auto_merge` is still
off at the repository level, so the Dependabot workflow in
[docs/dependabot-automerge.md](dependabot-automerge.md) polls the checks itself. If
`allow_auto_merge` is ever enabled, that workflow can be replaced by a one-line
`gh pr merge --auto`.

## Changing the list

Check names must match the job `name:` exactly, em-dash included. After renaming a job,
update the protection rule in the same change or the old context stays required and
never reports:

```bash
gh api -X PATCH repos/alahaouas/credit-simulator/branches/main/protection/required_status_checks \
  -f 'contexts[]=Detect code changes' -f 'contexts[]=Python — ruff + pytest' \
  -f 'contexts[]=Web — lint + typecheck + build' -f 'contexts[]=Web — Playwright E2E'
```
