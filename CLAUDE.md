# CLAUDE.md — AI Assistant Guide for credit-simulator

## Cost-Efficiency Rules

- No sub-agents unless genuine parallel isolation is required.
- Grep/Glob before Read; use `offset`+`limit` to read only needed lines.
- Read a file only when about to edit it.
- Batch independent tool calls in one message.
- Short responses — no recaps, no preambles.

---

This file provides context and conventions for AI assistants (e.g. Claude Code) working on this repository.

---

## Project Overview

**credit-simulator** is an interactive command-line mortgage / credit loan simulator. Given a property price, income, and savings, it finds the optimal loan plan, shows a full amortization schedule, and provides a down-payment sweet-spot analysis — all in the terminal.

---

## Repository State

Stack, tooling versions and lint rules are declared in `pyproject.toml` and `web/package.json` — read those rather than duplicating them here. The non-obvious constraints:

| Item | Constraint |
|---|---|
| Web stack | FastAPI (`api/`) + Next.js (`web/`) + Supabase auth/DB — see [docs/web-interface-plan.md](docs/web-interface-plan.md) for layer status |
| TypeScript toolchain (`web/`) | **Two TypeScript packages on purpose**: `typescript` (JS API — needed by `next build`, `typescript-eslint`, IDE) + `typescript-native` (npm alias of TypeScript 7) for `npm run typecheck`, ~6.4× faster. Both pinned caret-free. Use `npm run typecheck`, never `npx tsc`. See [docs/typescript-toolchain.md](docs/typescript-toolchain.md). |
| BE mortgage rates | Manually maintained in `profiles.py` (Belgium is excluded from the ECB MIR endpoint — unreliable, see `fetcher.py:17`). Refresh at runtime with `credit-simulator rates set ...` (see [docs/runtime-rates.md](docs/runtime-rates.md)). |
| Localisation | EN/FR via `i18n.py`; locale auto-detected from env/system; override with `--locale` flag |

---

## Git Workflow

### Branch Naming

- Feature branches created by Claude Code follow the pattern:
  `claude/<slug>-<session-id>`
  Example: `claude/claude-md-mluynvuq4laldf9u-B8TAO`
- Human feature branches should follow: `feature/<short-description>`
- Bug fixes: `fix/<short-description>`
- The default integration branch is `main`.

### Commit Conventions

Use clear, imperative-mood commit messages:

```
Add credit amortization calculator
Fix off-by-one error in interest computation
Refactor loan eligibility module for clarity
```

Never commit:
- Secrets, API keys, or credentials
- Build artifacts or generated files
- Editor-specific files (use `.gitignore`)

### Push Rules

- Always push to the branch you are working on:
  ```bash
  git push -u origin <branch-name>
  ```
- Never force-push to `main`.
- Branches prefixed with `claude/` are managed by Claude Code sessions.

---

## Development Setup

- **Language**: Python 3.11+
- **Package manager**: `pip` with `pyproject.toml` (PEP 517/518)
- **Key dependencies**:
  - `click` — CLI framework
  - `rich` — terminal formatting and tables
  - `requests` — online rate fetch
  - *(no ORM or DB — no persistent storage in v1)*
- **Dev dependencies** (`pip install -e ".[dev]"`):
  - `pytest` + `pytest-cov` — test runner + branch coverage gate
  - `pytest-mock` — mock fixtures for HTTP and external calls
  - `ruff` — linter (`ruff check src/ tests/`)
- **Run locally**: `python -m credit_simulator` (or `credit-simulator` once installed)
- **Run tests**: `python -m pytest` (coverage report printed automatically; gate: ≥ 90% on core modules)
- **Lint**: `ruff check src/ tests/`
- **Arithmetic**: Python built-in `decimal.Decimal` — **never `float` for monetary values**

### Environment Variables

No `.env` required for v1.

| Variable | Purpose |
|---|---|
| `FRED_API_KEY` | Required for US rate fetch via FRED API |
| `CREDIT_SIMULATOR_LOCALE` | Override interface language (`en` or `fr`); checked before `LANG` and system locale |

Never commit API keys.

---

## Core Modules

Under `src/credit_simulator/` (section refs point at `docs/requirements.md`). Glob for anything not listed; `tests/` mirrors these names (`unit/test_<module>.py`, plus `integration/test_cli.py`).

- `cli.py` — click CLI definition and interactive loop (Group with the `rates` subcommand)
- `rate_cli.py` — `rates set/show/clear/list/path` subcommand group
- `config.py` — application-wide constants and tuneable defaults
- `i18n.py` — translation registry (EN/FR), locale detection, `_()` helper
- `profiles.py` — static country profiles + `SessionProfileStore`
- `resolver.py` — parameter resolution (§4.1) and feasibility check (§4.2)
- `calculator.py` — EMI, amortization schedule, APR (§4.4)
- `optimizer.py` — grid-search optimizer (§4.3) + sweet-spot analysis (§4.5)
- `fetcher.py` — online rate fetch, ECB / BoE / FRED (§5.4)

---

## Coding Conventions

- **Clarity over cleverness**: Financial logic must be easy to audit.
- **Precision**: Use `decimal.Decimal` for all monetary values and rates — `float` is forbidden for monetary computations.
- **Immutability**: Use `dataclasses(frozen=True)` or `NamedTuple` for financial records.
- **Validation at boundaries**: Validate all inputs in `cli.py` before passing to core logic.
- **No silent failures**: Raise explicit exceptions for invalid financial states; surface them as readable CLI errors via `rich`.
- **Tests are mandatory**: Every calculation function must have unit tests with known expected values.
- **Insurance**: Applied as a fixed monthly amount = `original_principal × annual_insurance_rate / 12` — does not decrease with the outstanding balance.

---

## Testing Guidelines

- All core financial calculation functions require unit tests.
- Use table-driven / parameterized tests for formula verification.
- Test edge cases: zero interest, 100% LTV, maximum loan term, negative inputs, APR convergence at extreme rates.
- Structural invariants (LTV tier ascending order, effective rate positivity) must be asserted for every supported country — not just BE.
- Integration tests should use in-memory state only — never production data.
- Run `pytest` to execute the full suite with automatic branch coverage. The gate is **≥ 90%** for core modules (`cli.py` is excluded from the gate).
- External HTTP calls in fetcher tests must be mocked via `pytest-mock` — never make real network requests in tests.

---

## What AI Assistants Should Know

1. **Read before modifying**: Always read existing files before editing them.
2. **No speculative changes**: Only change what is explicitly requested or clearly necessary.
3. **Financial precision matters**: Flag any use of floating-point arithmetic for monetary values and suggest fixed-point or decimal alternatives.
4. **Security**: Never introduce SQL injection, command injection, or other OWASP Top 10 vulnerabilities. Validate and sanitize all external inputs.
5. **Minimal footprint**: Do not create extra files, helper utilities, or abstractions that are not required by the current task.
6. **Update this file**: When significant architectural decisions are made (stack choice, database, API design), update the relevant sections of this CLAUDE.md.
7. **Commit on the right branch**: All Claude Code work goes to the `claude/`-prefixed branch for the active session.

---

## Links & References

- Repository remote: `http://local_proxy@127.0.0.1:43216/git/alahaouas/credit-simulator`
- Owner: Alaeddine HAOUAS (@alahaouas)
- Initial commit: `e7ee26e` (2026-02-20)
