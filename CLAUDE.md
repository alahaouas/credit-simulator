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
| Source code | Not yet created |
| Framework / language | Not yet chosen |
| Build system | Not yet configured |
| Tests | Not yet written |
| CI/CD | Not yet configured |
| Documentation | Minimal (README only) |

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

## Development Setup (To Be Established)

When the technology stack is chosen, document here:

- **Language**: _TBD_
- **Runtime version**: _TBD_
- **Package manager**: _TBD_
- **Install dependencies**: _TBD_
- **Run locally**: _TBD_
- **Run tests**: _TBD_
- **Build for production**: _TBD_

### Environment Variables

Create a `.env` file based on `.env.example` (to be added). Never commit `.env`.

---

## Project Structure (Planned)

Once development begins, the repository should follow this layout:

```
credit-simulator/
├── CLAUDE.md           # This file
├── README.md           # Human-facing project overview
├── .env.example        # Template for environment variables
├── .gitignore          # Files to exclude from version control
├── src/                # Application source code
│   ├── core/           # Domain logic (credit models, calculations)
│   ├── api/            # HTTP API layer (if applicable)
│   └── utils/          # Shared utilities
├── tests/              # Automated tests
│   ├── unit/
│   └── integration/
├── docs/               # Extended documentation
└── scripts/            # Developer tooling scripts
```

Adjust this structure to match the chosen framework's conventions.

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

## Coding Conventions (To Be Finalized)

Until a specific stack is chosen, follow these general principles:

- **Clarity over cleverness**: Financial logic must be easy to audit.
- **Precision**: Use decimal/arbitrary-precision arithmetic for monetary values — never floating point for currency.
- **Immutability**: Prefer immutable data structures for financial records.
- **Validation at boundaries**: Validate all inputs at the edges of the system (API handlers, CLI entry points).
- **No silent failures**: Errors in financial calculations must be explicit and logged.
- **Tests are mandatory**: Every calculation function must have unit tests with known expected values.

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
