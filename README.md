# credit-simulator

An interactive command-line mortgage / credit loan simulator.
Given a property price, your income, and your savings, it finds the optimal
loan plan and walks you through an amortization schedule — all in your terminal.

> **Disclaimer**: rates embedded in this tool are reference values representing
> typical market conditions. They are not real-time rates and do not constitute
> financial advice. Always verify with your bank or broker.

---

## Features

- **Automatic parameter resolution** — country defaults fill in any value you
  don't provide (interest rate, insurance, down-payment ratio, max duration,
  debt-ratio limit, purchase taxes).
- **Five optimization modes** — minimize total cost, monthly payment, duration,
  down payment, or let the tool pick a balanced trade-off.
- **Full amortization schedule** — month-by-month breakdown of principal,
  interest, and insurance components.
- **Down-payment sweet-spot analysis** — automatically shown after every
  simulation. Compares the loan APR against a configurable opportunity-cost
  benchmark to identify the rational floor for your down payment. Highlights all
  LTV tier crossings (rate discounts and surcharge exits), the 6-month income
  reserve ceiling, and the absolute rate floor. When the minimum down payment
  falls in a surcharge LTV tier, the sweet spot is automatically raised to the
  cheapest exit from that penalty zone. When the best-tier APR dips below the
  opportunity cost rate, the sweet spot is capped at the rate floor rather than
  the reserve ceiling. If you set a preferred down payment, it appears as a
  "Your choice" row in the table so you can compare it instantly to the
  recommendation.
- **Interactive update loop** — change any parameter and re-run instantly;
  no restart needed.
- **Country profile overrides** — adjust any rate manually, or fetch the latest
  average mortgage rate live from a central bank API (ECB, Bank of England,
  FRED).
- **8 countries supported** — BE (default), FR, DE, ES, IT, PT, GB, US.
- **Multilingual UI** — English (default) and French. Locale auto-detected from
  the system; override with `--locale fr` or `CREDIT_SIMULATOR_LOCALE=fr`.
- **Decimal precision** — all monetary arithmetic uses `decimal.Decimal`;
  floating-point is never used for financial calculations.

---

## Requirements

- Python 3.11+
- `pip`

---

## Installation

```bash
git clone <repo-url>
cd credit-simulator
pip install -e ".[dev]"
```

Dev extras include `pytest`, `pytest-cov`, `pytest-mock`, and `ruff`.

---

## Usage

### Interactive mode (recommended)

```bash
python -m credit_simulator
```

The tool will prompt for mandatory inputs and optional overrides, then enter
the interactive loop:

```
Property price? 350000
Monthly net income? 6000
Available savings? 80000
[country defaults panel shown]
Use all country defaults and run immediately? [Y/n]:
Purchase taxes? [Enter for ~43 750 EUR, ? for help]:
Preferred down payment? [max 80 000, Enter to optimise, ? for help]:
Loan duration? [Enter for 20y (240 months), ? for help]:
Opportunity cost rate? [Enter for 3.5%, ? for help]:
```

### With CLI flags

All mandatory inputs can be passed as flags to skip the prompts:

```bash
python -m credit_simulator \
  --property-price 350000 \
  --income 6000 \
  --savings 80000 \
  --country BE \
  --quality average \
  --preference minimize_total_cost
```

Available flags:

| Flag | Description | Default |
|---|---|---|
| `--property-price` | Market price of the property | prompted |
| `--income` | Monthly net income | prompted |
| `--savings` | Maximum savings available for down payment | prompted |
| `--down-payment` | Intended down payment (pins optimizer to this amount) | optimizer finds the best |
| `--country` | ISO country code | `BE` |
| `--quality` | `average` or `best` | `average` |
| `--preference` | Optimization preference (see below) | `balanced` |
| `--duration` | Loan duration in months (e.g. `240`) or years (e.g. `20y`) | `20y` (240 months) |
| `--opp-rate` | Opportunity cost rate for sweet-spot analysis (e.g. `0.04` for 4%) | `3.5%` |
| `--locale` | Interface language: `en` or `fr` | auto-detected |

### Optimization preferences

| Preference | What it optimizes |
|---|---|
| `minimize_total_cost` | Minimizes total interest + insurance paid |
| `minimize_monthly_payment` | Minimizes the monthly installment |
| `minimize_duration` | Repays as fast as possible |
| `minimize_down_payment` | Preserves savings (smallest upfront amount) |
| `balanced` | System-chosen trade-off across all dimensions |

---

## Interactive loop commands

After each simulation result, you can type one of the following:

| Command | Action |
|---|---|
| `update` | Change any simulation parameter |
| `reset` | Reset a parameter to its country-profile default |
| `profile` | Update a country profile field (manual or online fetch) |
| `schedule` | Display the full month-by-month amortization schedule |
| `sweetspot` | Re-display the sweet-spot analysis (also shown automatically after each run) |
| `params` | Show all current parameter values and their sources |
| `exit` | Quit the session |

### Example session

```
> update
  Fields: annual_interest_rate, available_savings, country, ...
Field to update: annual_interest_rate
New annual interest rate (e.g. 0.035): 0.029

> update
Field to update: optimization_preference
  Preferences: balanced, minimize_down_payment, minimize_duration, ...
Optimization preference: minimize_monthly_payment

> schedule
[amortization table printed]

> exit
Goodbye.
```

---

## Supported countries

| Country | Code | Currency | Avg rate | Best rate | Max duration |
|---|---|---|---|---|---|
| Belgium _(default)_ | `BE` | EUR | 3.40% | 3.20% | 25 years |
| France | `FR` | EUR | 3.50% | 2.90% | 25 years |
| Spain | `ES` | EUR | 3.50% | 2.80% | 30 years |
| Germany | `DE` | EUR | 3.80% | 3.10% | 30 years |
| Portugal | `PT` | EUR | 4.00% | 3.20% | 30 years |
| Italy | `IT` | EUR | 4.00% | 3.20% | 30 years |
| United Kingdom | `GB` | GBP | 5.00% | 4.20% | 35 years |
| United States | `US` | USD | 7.00% | 6.20% | 30 years |

Regulatory parameters (purchase tax rate, minimum down payment, maximum
debt-to-income ratio) are embedded per country and can be overridden manually
during a session.

---

## Refreshing rates between releases

Market rates change faster than releases. Use `credit-simulator rates` to
override the bundled rates at runtime — the change persists across sessions
and survives upgrades that don't ship newer numbers.

```pwsh
credit-simulator rates set BE annual_rate_best 0.0310
credit-simulator rates show BE
```

Full reference: [docs/runtime-rates.md](docs/runtime-rates.md).

---

## Online rate fetch

For Eurozone countries, GB, and US, you can fetch the latest average market
rate from a public central bank API:

```
> profile
Update mode (manual / online): online
Country code: FR
Fetching latest average annual rate for FR...
Applied fetched rate: 3.4500% for FR average
```

| Country | Source |
|---|---|
| BE, FR, DE, ES, IT, PT | ECB Data Portal (`MIR` series) |
| GB | Bank of England Statistics API |
| US | FRED API — requires `FRED_API_KEY` environment variable |

Only the `average` quality rate can be fetched (central banks publish
population-average rates; competitive "best" rates have no public API).

---

## Localisation

The interface is available in English and French. The locale is selected in
this order:

1. `CREDIT_SIMULATOR_LOCALE` environment variable (`en` or `fr`)
2. `LANG` environment variable (e.g. `fr_BE.UTF-8`)
3. System locale (`locale.getlocale()`)
4. Fallback: `en`

Override at runtime with the `--locale` flag:

```bash
python -m credit_simulator --locale fr
```

---

## Project structure

```
credit-simulator/
├── pyproject.toml
├── docs/
│   └── requirements.md     # Full product specification
├── src/
│   └── credit_simulator/
│       ├── __main__.py     # Entry point
│       ├── cli.py          # Interactive CLI and update loop
│       ├── config.py       # Application-wide constants and defaults
│       ├── i18n.py         # Translation registry (EN / FR) and locale helpers
│       ├── profiles.py     # Country profiles + session-scoped store
│       ├── resolver.py     # Parameter resolution and feasibility check
│       ├── calculator.py   # EMI, amortization schedule, APR
│       ├── optimizer.py    # Grid-search optimizer and sweet-spot analysis
│       └── fetcher.py      # Online rate fetch (ECB / BoE / FRED)
└── tests/
    ├── unit/
    │   ├── test_calculator.py
    │   ├── test_profiles.py
    │   ├── test_optimizer.py
    │   ├── test_resolver.py
    │   └── test_fetcher.py
    └── integration/
        └── test_cli.py
```

---

## Running tests

```bash
python -m pytest
```

`pytest` is pre-configured (via `pyproject.toml`) to run with branch coverage
enabled and produce a terminal missing-lines report. Core modules must maintain
**≥ 90% branch coverage** — the build fails if the gate is not met.

Test suite covers:
- EMI arithmetic, amortization schedule invariants, APR convergence and round-trip accuracy
- All optimization preferences and sweet-spot analysis (including LTV surcharge-zone handling)
- Country profile structural invariants (LTV tier ordering, effective rate positivity) for all 8 countries
- Parameter resolution, feasibility checks, and edge cases
- Online rate fetcher with mocked HTTP responses
- CLI integration (smoke tests)

### Linting

```bash
ruff check src/ tests/
```

`ruff` is configured for Python 3.11 with rules E, F, W, I (import order), UP (pyupgrade), B (flake8-bugbear), and SIM (simplification).

---

## Key formulas

**EMI** (Equated Monthly Installment — principal + interest only):

```
EMI = P x r x (1 + r)^n / ((1 + r)^n - 1)
```

**Monthly insurance** (fixed, applied to original principal):

```
insurance = P x annual_insurance_rate / 12
```

**Total monthly payment**:

```
payment = EMI + insurance
```

All intermediate values use `decimal.Decimal` with half-up rounding to 2
decimal places for display.

---

## Out of scope (v1)

- Variable / adjustable interest rates
- Co-borrower scenarios
- Persistent storage
- Background rate polling
- PTZ or state-subsidized loan blending
