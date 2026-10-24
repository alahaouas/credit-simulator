# AGENTS.md — working on a branch, for every coding agent

Claude Code, Gemini, Jules and any other agent read this file. Project context and
conventions are in [`CLAUDE.md`](CLAUDE.md) and `docs/`: do not repeat them here. This file covers merging, cleaning up, and what a brief costs.

Every rule below comes from an incident measured on a sibling repository
(cyber-kitten, 2026-10-11) and applies here because the setup is the same: several
agents, several git worktrees, one GitHub account.

## Merging

- The human merges, or delegates it **in the current session**: either a named PR
  ("merge #N"), or a standing rule with conditions ("merge each PR when CI is green and
  the review is clean"). With a standing rule, merge only PRs that meet every condition
  and say in a PR comment which ones you checked.
- "Once #N is merged, do X" is **not** a delegation. Wait for the human to merge it.
  Never write that sentence to another agent either: say "when the human has merged #N".
- Before merging: CI has run and is green on the head you read (an empty check list is
  not green), the PR is not a draft, review findings are answered.
- Use the repository's usual merge method (merge commits here, as the recent history shows).
- **Never pass `--delete-branch`.** `gh pr merge --delete-branch` removes every worktree
  that has the branch checked out, whichever agent owns it, and git commands run from the
  emptied directory then act on the main checkout. GitHub already deletes the merged head
  branch.

## Cleaning up

1. `git fetch --all --prune` drops the remote branches GitHub already deleted.
2. Delete your **own** merged local branches with `git branch -d <name>`. Run
   `git worktree list` first: a branch checked out in a worktree cannot be deleted, and
   that worktree belongs to someone.
3. Remove only **your own** worktree, after leaving its directory, with
   `git worktree remove <path>` from the main checkout. Look first with
   `git status --short --ignored`: untracked scratch files and local settings go with it.
4. Cleaning other agents' leftovers (old worktrees under `.claude/worktrees/`, stale
   branches) is the human's job, or an agent's when the human asks in the current session.
   The request sets a scope ("merged branches", "everything before today"). Look, report,
   and remove only what clearly falls inside it; anything in use or with uncommitted work
   is left and reported.
5. After a cleanup, check that your worktree still has its `.git` file and that
   `git rev-parse --show-toplevel` points to it before any state-changing command.

## Briefs and cost

The brief sets the cost, not the model. Measured: a six-check QA brief with no limits cost
$9.21 on a cheap model and found one real defect.

**Writing a brief or a review for another agent**
- Give a budget (dollars or steps) and a stop rule: two failed attempts at a step, record
  it as blocked with the evidence and move on.
- List the acceptance criteria in the brief, so review does not cause a rework round.
- Cap the output: document at most 100 lines, self-review at most 15, at most five
  screenshots, numbers from a script rather than narrative.
- A model without image input gets only scripted checks.
- In a review, never write "either test it or reword it": name the cheap path, say which
  findings need no new run, batch the findings, and put any cap in the review itself.

**Receiving one**
- Report at half the budget; stop at the cap and publish what you have.
- Save evidence to files, keep one log line per check, and look at an image only when you
  must judge it. Never read an image wider than about 1000 px: downscale first.
- Sign every commit with the agent that wrote it, `Co-Authored-By: <Agent> <address>`.
