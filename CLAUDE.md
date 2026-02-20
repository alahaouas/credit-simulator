# CLAUDE.md — AI Assistant Guide for credit-simulator

This file provides context and conventions for AI assistants (e.g. Claude Code) working on this repository.

---

## Project Overview

**credit-simulator** is a project for simulating credit-related financial scenarios. As of the initial commit, the project is in its bootstrapping phase — no application code, framework, or tooling has been added yet.

This document should be updated as the project evolves.

---

## Repository State (as of 2026-02-20)

| Item | Status |
|---|---|
| Source code | **In progress** — initial implementation on `claude/explain-codebase-mlvdnzl75enhzw3c-v8Qnv` |
| Framework / language | **Python 3.11+** (chosen) |
| Build system | `pyproject.toml` (PEP 517/518, `hatchling`) |
| Tests | Unit + integration tests under `tests/` |
| CI/CD | Not yet configured |
| Documentation | Requirements doc complete (`docs/requirements.md`) |

---

## Git Workflow

### Branch Naming

- Feature branches created by Claude Code follow the pattern:
  `claude/<slug>-<session-id>`
  Example: `claude/claude-md-mluynvuq4laldf9u-B8TAO`
- Human feature branches should follow: `feature/<short-description>`
- Bug fixes: `fix/<short-description>`
- The default integration branch is `master`.

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
- Never force-push to `master`.
- Branches prefixed with `claude/` are managed by Claude Code sessions.

---

## Development Setup

- **Language**: Python 3.11+
- **Package manager**: `pip` with `pyproject.toml` (PEP 517/518)
- **Key dependencies**:
  - `click` — CLI framework
  - `rich` — terminal formatting and tables
  - *(no ORM or DB — no persistent storage in v1)*
- **Install dependencies**: `pip install -e ".[dev]"`
- **Run locally**: `python -m credit_simulator` (or `credit-simulator` once installed)
- **Run tests**: `pytest`
- **Arithmetic**: Python built-in `decimal.Decimal` — **never `float` for monetary values**

### Environment Variables

No `.env` required for v1. The FRED API key (needed for US rate fetch) will be read from the environment variable `FRED_API_KEY` when that feature is implemented. Never commit API keys.

---

## Project Structure

```
credit-simulator/
├── CLAUDE.md                   # This file
├── README.md                   # Human-facing project overview
├── pyproject.toml              # Package metadata and dependencies
├── .gitignore
├── docs/
│   └── requirements.md         # Full product specification
├── src/
│   └── credit_simulator/
│       ├── __main__.py         # Entry point: `python -m credit_simulator`
│       ├── cli.py              # click CLI definition and interactive loop
│       ├── profiles.py         # Static country profiles data
│       ├── resolver.py         # Parameter resolution (§4.1)
│       ├── calculator.py       # EMI, amortization, APR (§4.4)
│       ├── optimizer.py        # Grid-search optimizer (§4.3)
│       └── fetcher.py          # Online rate fetch — ECB / BoE / FRED (§5.4)
└── tests/
    ├── unit/
    │   ├── test_calculator.py
    │   ├── test_optimizer.py
    │   └── test_resolver.py
    └── integration/
        └── test_cli.py
```

---

## Domain Concepts

When implementing features, be aware of these credit-domain terms:

| Term | Meaning |
|---|---|
| Principal | The original loan amount borrowed |
| Interest rate | The percentage charged on the principal |
| APR | Annual Percentage Rate — total yearly cost of a loan |
| Amortization | Spreading loan payments over a schedule |
| EMI | Equated Monthly Installment |
| LTV | Loan-to-Value ratio |
| Credit score | Numerical representation of creditworthiness |
| Default | Failure to repay a loan per agreed terms |

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
- Test edge cases: zero interest, 100% LTV, maximum loan term, negative inputs.
- Integration tests should use a dedicated test database or in-memory store — never production data.

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
