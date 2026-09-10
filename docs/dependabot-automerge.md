# Dependabot auto-merge

`.github/workflows/dependabot-automerge.yml` squash-merges Dependabot pull requests
that are **patch or minor**, once every other check on the PR is green. Majors are
left open for a human.

## Why a workflow rather than GitHub's own auto-merge

`gh pr merge --auto` needs two things this repository does not have: `allow_auto_merge`
on the repository, and branch protection on `main` with required status checks. Without
required checks there is nothing for auto-merge to wait on, so it merges immediately —
which is the opposite of the intent. Enabling protection is the cleaner long-term fix,
but it changes how everyone pushes to `main`, so the workflow polls the checks itself
instead.

It also runs entirely on `GITHUB_TOKEN` and GitHub's Actions budget. A Claude-driven
alternative would authenticate with `CLAUDE_CODE_OAUTH_TOKEN`, which draws on the same
five-hour session pool as local sessions and can empty it unattended.

## What it does

| Step | Behaviour |
|---|---|
| Gate | Runs only when `pull_request.user.login == 'dependabot[bot]'` and the PR is not a draft |
| Metadata | `dependabot/fetch-metadata` (pinned to a SHA) reports the update type |
| Majors | `version-update:semver-major` sets `SKIP=1` and the PR is left open with a notice |
| Wait | Polls `gh pr checks` every 30 s, up to 25 minutes |
| Merge | `gh pr merge --squash --delete-branch` |

For a **grouped** PR, `update-type` is the highest in the group — one major anywhere in
the group holds the whole PR back.

## Two details that are easy to get wrong

**The wait step excludes this workflow's own job by name.** A `pull_request_target` run
can surface in the PR's own check list, so `gh pr checks --watch` can end up waiting on
itself and never returns.

**`gh pr checks` exits non-zero when checks are pending (8) or failing (1).** Under
`set -e` that aborts the step before the JSON is read, so the call tolerates a non-zero
status and the parsed state is what decides. A PR with no checks reported yet parses as
an empty array and keeps waiting.

## Security

`pull_request_target` runs with the base repository's token and write permissions, so
the workflow must never check out or execute the PR's code. It does not — every step
talks to the GitHub API only. Do not add an `actions/checkout` step to this file.

## Related configuration

`.github/dependabot.yml` already groups npm minor/patch updates into a single
`web-minor-patch` PR and ignores majors for `next`, `react`, `react-dom` and
`eslint-config-next`. Grouping matters beyond noise: separate PRs that each touch
`web/package-lock.json` conflict with one another, and GitHub reports every one of them
as mergeable until the first one merges.

Transitive-only bumps fall outside the declared-dependency groups and still arrive as
their own PR (`@babel/core` in #232, for example).
