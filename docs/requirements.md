# Requirements — credit-simulator

## 1. Problem Statement

A buyer acquires a property and must finance part of its total acquisition cost through a bank loan. The total acquisition cost includes the property price and the associated purchase taxes (notary fees, registration taxes, agency fees, etc.).

The simulator must determine the **optimal combination** of:
- **Down payment** (apport initial) — the amount paid upfront by the buyer
- **Monthly installment** (mensualité) — the recurring loan repayment amount
- **Loan duration** — the number of months over which the loan is repaid

**Example**: property at 499,000 EUR + 68,000 EUR in purchase taxes → total acquisition cost of 567,000 EUR.

---

## 2. Inputs

### 2.1 Property Inputs

| Field | Description | Required | Constraints |
|---|---|---|---|
| `property_price` | Market price of the property | Yes | > 0 |
| `country` | ISO 3166-1 alpha-2 code of the country where the property is located | No | e.g. `"FR"`, `"ES"`, `"DE"`; defaults to `"BE"` |
| `profile_quality` | Which rate variant of the country profile to use | No | `average` (default) or `best` |
| `purchase_taxes` | Total purchase taxes and fees (notary, registration, agency) | No | >= 0; auto-estimated from country profile if omitted |
| `total_acquisition_cost` | Derived: `property_price + purchase_taxes` | — | Computed, never entered directly |

### 2.2 Loan Parameters

All fields in this section are **optional**. When a field is not provided, the system resolves it automatically from the country profile (see section 2.4). Any explicitly provided value always overrides the country default.

| Field | Description | Constraints |
|---|---|---|
| `annual_interest_rate` | Bank's nominal annual interest rate | > 0 |
| `insurance_rate` | Annual borrower insurance rate | >= 0 |
| `min_down_payment_ratio` | Minimum down payment as a fraction of total acquisition cost | 0%–100% |
| `max_loan_duration_months` | Maximum acceptable loan duration | 12–600 months |
| `fixed_loan_duration_months` | Pin the loan to an exact duration instead of optimizing over it | 12–`max_loan_duration_months`; defaults to 240 months (20 years) if omitted |

> **Note**: Whether purchase taxes are financeable by the bank is country-specific and defined in the country profile. For example, in France taxes are not financeable, so the minimum down payment always covers at least `purchase_taxes`.

### 2.3 Buyer Constraints

| Field | Description | Required | Constraints |
|---|---|---|---|
| `monthly_net_income` | Buyer's total monthly net income | Yes | > 0 |
| `available_savings` | **Maximum** savings available — the absolute ceiling the buyer can draw on for the down payment | Yes | >= 0 |
| `preferred_down_payment` | Intended down payment — the specific amount the buyer plans to contribute at acquisition | No | >= `min_down_payment`, <= `available_savings`; if omitted the optimizer searches the full range |
| `max_debt_ratio` | Maximum debt-to-income ratio | No | > 0; defaults to country profile value |
| `max_monthly_payment` | Hard cap on monthly installment | No | > 0; defaults to 2,200 EUR (or equivalent in country currency) |

### 2.4 Country Profiles

The system embeds a static reference table for each supported country. Each country has two **profile qualities**:

| Quality | Description |
|---|---|
| `average` _(default)_ | Typical market rates — represents what most borrowers obtain |
| `best` | Lowest competitive rates — represents the lowest rates available to well-qualified borrowers from top-tier lenders or brokers; always ≤ `average` |

Profile quality only affects **market-driven fields** (`annual_interest_rate`, `insurance_rate`). Regulatory fields (purchase taxes, minimum down payment, maximum debt ratio, maximum duration) are identical across both qualities and cannot be set to "best" since they are fixed by law or banking regulation.

**Default country**: `BE` (Belgium) — used when `country` is not provided.

**Market-driven rates (vary by profile quality):**

| Country | Code | Currency | Avg Interest Rate | Best Interest Rate | Avg Insurance Rate | Best Insurance Rate |
|---|---|---|---|---|---|---|
| France | `FR` | EUR | 3.50% | 2.90% | 0.30% | 0.10% |
| Spain | `ES` | EUR | 3.50% | 2.80% | 0.20% | 0.09% |
| Germany | `DE` | EUR | 3.80% | 3.10% | 0.15% | 0.08% |
| Portugal | `PT` | EUR | 4.00% | 3.20% | 0.25% | 0.10% |
| Belgium _(default)_ | `BE` | EUR | 3.60% | 2.90% | 0.25% | 0.10% |
| Italy | `IT` | EUR | 4.00% | 3.20% | 0.20% | 0.08% |
| United Kingdom | `GB` | GBP | 5.00% | 4.20% | 0.25% | 0.12% |
| United States | `US` | USD | 7.00% | 6.20% | 0.80% | 0.40% |

**Regulatory parameters (same for both profile qualities):**

| Country | Code | Purchase Tax Rate | Min Down Payment | Max Debt Ratio | Max Duration |
|---|---|---|---|---|---|
| France | `FR` | 7.5% of price (old) / 2.5% (new) | covers taxes (not financeable) | 35% | 25 years |
| Spain | `ES` | 8.0% of price (ITP resale) | 20% of price | 35% | 30 years |
| Germany | `DE` | 5.0% of price (avg Grunderwerbsteuer + notary) | 20% of price | 35% | 30 years |
| Portugal | `PT` | 7.0% of price (IMT + stamp + notary) | 10% of price (residents) | 35% | 30 years |
| Belgium _(default)_ | `BE` | 12.5% of price (registration, Wallonia/Brussels) | 20% of price | 35% | 25 years |
| Italy | `IT` | 4.0% of price (avg cadastral + notary) | 20% of price | 35% | 30 years |
| United Kingdom | `GB` | 3.0% of price (avg SDLT) | 10% of price | 35% | 35 years |
| United States | `US` | 2.5% of price (avg closing costs) | 20% of price (conventional) | 43% | 30 years |

> **Disclaimer**: These are reference values representing typical market conditions. They are not real-time rates and do not constitute financial advice. Users are encouraged to provide actual bank-quoted rates for precise results.

**Profile fields per country:**

| Field | Quality-sensitive | Description |
|---|---|---|
| `currency` | No | ISO 4217 currency code for monetary outputs |
| `annual_rate` | **Yes** | Default `annual_interest_rate`; varies between `average` and `best` |
| `insurance_rate` | **Yes** | Default `insurance_rate`; varies between `average` and `best` |
| `purchase_tax_rate` | No | Used to estimate `purchase_taxes`: `property_price × rate` |
| `taxes_financeable` | No | Boolean — whether purchase taxes can be included in the loan principal |
| `min_down_payment_ratio` | No | Default minimum down payment ratio |
| `max_debt_ratio` | No | Default maximum debt-to-income ratio (e.g. 0.35 = 35%) |
| `max_loan_duration_months` | No | Default maximum loan duration |

### 2.5 Optimization Preferences

The buyer may optionally specify which objective to prioritize. Defaults to `balanced` if not provided.

| Preference | Description |
|---|---|
| `minimize_total_cost` | Minimize total interest + insurance paid over the loan life |
| `minimize_monthly_payment` | Minimize the monthly installment |
| `minimize_duration` | Repay the loan as fast as possible |
| `minimize_down_payment` | Preserve savings by contributing as little upfront as possible |
| `balanced` | System-driven trade-off across all dimensions (default) |

---

## 3. Outputs

### 3.1 Recommended Loan Plan

| Field | Description |
|---|---|
| `country` | Country code used |
| `profile_quality` | Profile quality used (`average` or `best`) |
| `currency` | Currency of all monetary outputs (from country profile) |
| `parameters_source` | For each loan parameter: `"user"` if explicitly provided, `"country_profile"` if auto-resolved |
| `down_payment` | Recommended initial amount paid by the buyer |
| `loan_principal` | Amount borrowed from the bank (`total_acquisition_cost - down_payment`) |
| `loan_duration_months` | Recommended duration in months |
| `monthly_installment` | Monthly payment (principal + interest + insurance) |
| `monthly_interest` | Interest component of the first installment |
| `monthly_insurance` | Insurance component of the monthly installment |
| `effective_annual_rate` (APR) | True annual percentage rate including all fees |
| `total_interest_paid` | Sum of all interest payments over the loan life |
| `total_insurance_paid` | Sum of all insurance payments over the loan life |
| `total_cost_of_credit` | `total_interest_paid + total_insurance_paid` |
| `total_repaid` | `loan_principal + total_cost_of_credit` |
| `debt_ratio` | `monthly_installment / monthly_net_income` |
| `ltv_ratio` | `loan_principal / property_price` |

### 3.2 Amortization Schedule

For each monthly period from 1 to `loan_duration_months`:

| Column | Description |
|---|---|
| `period` | Month number |
| `opening_balance` | Remaining principal at start of period |
| `monthly_installment` | Total payment for this period |
| `principal_component` | Portion repaying the principal |
| `interest_component` | Portion covering interest |
| `insurance_component` | Portion covering insurance |
| `closing_balance` | Remaining principal after payment |

### 3.3 Scenario Comparison (optional)

When multiple optimization preferences are evaluated, the system shall return one recommended plan per preference, formatted for side-by-side comparison.

---

## 4. Optimization Logic

### 4.1 Parameter Resolution

Before any computation, the system resolves all loan parameters in this order:

1. If `country` is not provided, default it to `BE`. If `profile_quality` is not provided, default it to `average`. Load the country profile for the resolved code and quality. If the country code is not supported, return an explicit error.
2. For each optional loan parameter (`annual_interest_rate`, `insurance_rate`, `min_down_payment_ratio`, `max_loan_duration_months`, `max_debt_ratio`): use the user-supplied value if provided, otherwise use the value from the selected profile variant (`average` or `best`).
3. If `purchase_taxes` is not provided, estimate it as `property_price × country_profile.purchase_tax_rate`.
4. Compute `total_acquisition_cost = property_price + purchase_taxes`.
5. Determine the effective minimum down payment:
   - If `country_profile.taxes_financeable = false`: `min_down_payment = max(purchase_taxes, total_acquisition_cost × min_down_payment_ratio)`
   - If `country_profile.taxes_financeable = true`: `min_down_payment = total_acquisition_cost × min_down_payment_ratio`

### 4.2 Feasibility Check (pre-optimization)

Before optimizing, the system shall verify:
1. `available_savings >= min_down_payment` — the buyer can cover the minimum required down payment.
2. `monthly_net_income * max_debt_ratio >= minimum_possible_monthly_payment` — the buyer can afford any loan at all.
3. The required loan amount is positive.

If any check fails, the system must return an **ineligibility result** with a clear, specific reason.

### 4.3 Optimization Algorithm

Given the buyer's preference, the system shall search over the space of:
- Down payment amounts: from `min_down_payment` up to `available_savings` (step: 1,000 in the country currency)
- Loan durations: from 12 months up to `max_loan_duration_months` (step: 12 months)

For each `(down_payment, duration)` pair, compute the resulting plan and check all constraints:
- `monthly_installment <= effective_monthly_cap` where `effective_monthly_cap = min(monthly_net_income × max_debt_ratio, max_monthly_payment)`
- `loan_principal > 0`

Among all **feasible** plans, select the one that best satisfies the declared preference.

### 4.4 EMI Formula

The standard reducing-balance monthly installment formula applies:

```
EMI = P × r × (1 + r)^n / ((1 + r)^n − 1)
```

Where:
- `P` = loan principal
- `r` = monthly interest rate = `annual_rate / 12`
- `n` = loan duration in months
- Insurance is added on top: `monthly_payment = EMI + (P × annual_insurance_rate / 12)` — insurance is computed on the **original principal** `P` and remains constant for the life of the loan

> **Precision requirement**: all intermediate and final monetary values must use decimal fixed-point arithmetic. Floating-point types are forbidden for monetary computations.

### 4.5 Down-Payment Sweet-Spot Analysis

After every simulation result the system automatically produces a sweet-spot milestone table that helps the buyer choose a rational down payment. The table can also be re-displayed at any time using the `sweetspot` interactive command.

#### Decision rule

For a fixed-rate mortgage the marginal interest saving per extra unit of down payment is **constant within an LTV tier**. The sweet spot is therefore determined by an opportunity-cost comparison:

| Condition | Sweet spot |
|---|---|
| Loan APR > opportunity-cost rate | Maximise down payment up to the 6-month income reserve ceiling |
| Loan APR ≤ opportunity-cost rate | Use the **effective floor** (see below) and invest the rest |

The default **opportunity-cost rate** is **3.5 %** (configurable in `config.py`).

#### Effective floor (surcharge zone rule)

When the minimum down payment results in an LTV that falls in a **surcharge tier** (rate_delta > 0), anchoring the sweet spot at that minimum is irrational: a small extra payment exits the penalty zone and almost always delivers a saving that exceeds any opportunity-cost argument.

**Rule**: when the minimum down payment is in a surcharge tier, the sweet spot floor is the minimum down payment that exits the surcharge zone (i.e., the cheapest down payment reaching the highest-LTV non-surcharge tier). The opportunity-cost APR comparison is also evaluated at this effective floor, not at the raw minimum.

**Example**: BE best profile, 499 000 EUR property + 68 000 EUR taxes (total 567 000 EUR).
Minimum down payment = 113 400 EUR → LTV = 90.9 % → surcharge tier (+0.35 %).
Effective floor = 118 000 EUR → LTV ≤ 90 % → base tier (0.35 % penalty gone).
Even if loan APR < opportunity-cost rate at the floor, the sweet spot is 118 000 EUR, not 113 400 EUR.

#### Milestone table

The table always shows:

| Milestone | Condition |
|---|---|
| Minimum | Absolute minimum down payment (`min_down_payment`) |
| LTV≤X% rate↓ | Each LTV tier crossing that reduces the interest rate |
| ★ Sweet spot | The recommended down payment per the rule above |
| Xm reserve cap | Maximum down payment while keeping X months of income in reserve |
| Maximum | Full available savings |

Each row shows: down payment, applicable interest rate, monthly installment, DTI ratio, LTV ratio, total cost of credit, and liquidity remaining.

When a `preferred_down_payment` is set, the table includes an additional **"Your choice"** milestone at that amount (or appends "← Your choice" to an existing row if the amounts coincide), rendered in a distinct colour so the buyer can immediately compare their intended contribution to the optimizer's recommendation.

---

## 5. Interactive Parameter Update Loop

After displaying simulation results, the system shall enter an interactive prompt that lets the user modify any input parameter and re-run the simulation without restarting the session.

### 5.1 Session Startup

At the start of a session, the system prompts for mandatory parameters and optional overrides:

| Parameter | Prompt | Required |
|---|---|---|
| `property_price` | "Property price?" | Yes |
| `monthly_net_income` | "Monthly net income?" | Yes |
| `available_savings` | "Available savings (maximum you can use for down payment)?" | Yes |
| `purchase_taxes` | "Purchase taxes? (press Enter to estimate from country profile)" | No |
| `preferred_down_payment` | "Preferred down payment? (press Enter to let optimizer find the best)" | No |

All other parameters are optional at startup and resolved automatically (see section 2). Once the mandatory values are collected, the system runs an initial simulation — including the sweet-spot analysis — and displays the results before entering the update loop.

### 5.2 Behaviour

1. After each result is shown, the system automatically displays the **sweet-spot analysis** (see §4.5), then prints the available actions and prompts the user. The current parameter values (including source attribution) can be inspected at any time with the `params` command. Available actions:
   - Update one or more simulation parameters
   - Change the optimization preference
   - Reset a parameter to its country-profile default
   - Update a country profile field — manually or via online fetch (see §5.4)
   - Exit the session

2. The user selects a parameter by name, enters the new value, and the system validates it immediately using the same rules as the initial input (§2).

3. On valid input, the system re-runs full parameter resolution (§4.1), feasibility check (§4.2), and optimization (§4.3), then displays the new result.

4. On invalid input, the system displays an inline error and re-shows the prompt — no full restart required.

5. The loop repeats until the user explicitly exits.

### 5.3 Updatable Parameters

All fields from sections 2.1, 2.2, and 2.3 are updatable interactively, except derived fields (`total_acquisition_cost`). The optimization preference (section 2.5) is also updatable.

| Category | Updatable fields |
|---|---|
| Property | `property_price`, `country`, `profile_quality`, `purchase_taxes` |
| Loan parameters | `annual_interest_rate`, `insurance_rate`, `min_down_payment_ratio`, `max_loan_duration_months`, `fixed_loan_duration_months` |
| Buyer constraints | `monthly_net_income`, `available_savings`, `preferred_down_payment`, `max_debt_ratio`, `max_monthly_payment` |
| Preference | `optimization_preference` |
| Country profile | Any market-driven or regulatory field for any supported country (see §5.5) |

### 5.4 Country Profile Updates

The user may update any field of any country profile during the interactive loop. Two update modes are available: **manual entry** and **online fetch**.

**Scope**: all profile updates are session-scoped — they are not persisted to disk. The static embedded profiles are restored at the next session start.

---

**Mode A — Manual entry**

1. User selects "Update a country profile field" → "Enter manually".
2. System asks: which country? (must be a supported code)
3. System asks: which quality to update? (`average` or `best`) — only for quality-sensitive fields
4. System asks: which field?
5. System asks: new value? (validated immediately)
6. On valid input, the updated value is stored in session state and the simulation re-runs.

---

**Mode B — Online fetch**

The system can retrieve the current average market interest rate from a public central bank API on demand, without the user having to enter values manually.

1. User selects "Update a country profile field" → "Fetch from online".
2. System asks: which country?
3. System contacts the configured data source (see "Data sources" below) and retrieves the latest `annual_rate` for the `average` quality of the selected country.
4. **Auto-apply rule**:
   - If the user has **not** manually overridden `annual_rate` for that country/quality in the current session → the fetched value is applied immediately without prompting.
   - If the user **has** manually overridden `annual_rate` → the system shows the fetched value alongside the current override and asks for confirmation before replacing it.
5. If the online fetch fails (network error, source unavailable, data not found), the system displays a clear error message and offers to fall back to manual entry.

> **Scope constraints**:
> - Only `annual_rate` (`average` quality) can be fetched. Central banks publish population-average new-business rates; best/competitive rates are broker-specific and have no public API.
> - `insurance_rate` has no public data source and must be updated manually.
> - Regulatory fields are not fetched — they must be updated manually.

---

**Data sources by country:**

| Country | Code | Source | Series / endpoint |
|---|---|---|---|
| Eurozone (BE, FR, DE, ES, IT, PT) | — | ECB Data Portal API | `GET https://data.ecb.europa.eu/api/v1/data/MIR/M.{CC}.B.A2C.F.R.A.2250.EUR.N?lastNObservations=1&format=jsondata` — no authentication required |
| United Kingdom | `GB` | Bank of England Statistics API | Effective mortgage rate series (exact key TBD at implementation) |
| United States | `US` | FRED API (Federal Reserve Bank of St. Louis) | Series `MORTGAGE30US` (30-year fixed, weekly) — free API key required |

The ECB series key `MIR.M.{CC}.B.A2C.F.R.A.2250.EUR.N` encodes: monthly frequency · country code · new business · housing loans (A2C) · annualised agreed rate · households · EUR. Data is published on the 23rd working day after each reference month.

---

**Updatable profile fields:**

| Field | Quality-sensitive | Manual | Online fetch | Validation |
|---|---|---|---|---|
| `annual_rate` | Yes (`average` / `best`) | Yes | `average` only | > 0 |
| `insurance_rate` | Yes (`average` / `best`) | Yes | No | >= 0 |
| `purchase_tax_rate` | No (shared) | Yes | No | >= 0 |
| `taxes_financeable` | No (shared) | Yes | No | `true` or `false` |
| `min_down_payment_ratio` | No (shared) | Yes | No | 0%–100% |
| `max_debt_ratio` | No (shared) | Yes | No | > 0, ≤ 1 |
| `max_loan_duration_months` | No (shared) | Yes | No | 12–600 |

> **Invariant**: `best` rates must always be ≤ the corresponding `average` rates. The system rejects any manual update that would violate this and displays an explicit error.

### 5.5 State Management

- The system maintains a **mutable parameter state** and a **mutable profile store** for the duration of the session.
- Each update is applied on top of the current state (not from scratch): unchanged parameters keep their previous values.
- Resetting a parameter removes the user-supplied override and restores the country-profile default.
- If `country` or `profile_quality` is changed, all parameters previously auto-resolved from the old profile are re-resolved from the new profile/quality, except those explicitly set by the user.
- If a country profile field is updated (§5.4), all parameters currently resolved from that country/quality pair are immediately re-resolved, except those explicitly set by the user.

---

## 6. Non-Functional Requirements

### 6.1 Precision
- All monetary values use fixed-point / decimal arithmetic.
- Rounding: half-up, to 2 decimal places for display, full precision for intermediate steps.

### 6.2 Validation
- All inputs validated at the system boundary with explicit, descriptive error messages.
- Rejected values: non-positive prices, negative rates, durations below 12 months or above the country profile maximum, savings below the minimum required down payment.

### 6.3 Performance
- Full optimization search over all `(down_payment, duration)` pairs must complete in under 1 second for a standard 300-month / 1,000 EUR step search space.
- Amortization schedule generation for a 300-month loan must complete in under 200 ms.

### 6.4 Testability
- Every calculation function (EMI, APR, amortization row, debt ratio) must have unit tests with known expected values.
- Optimizer must have integration tests covering each preference mode.
- Edge cases: zero insurance, minimum duration (12 months), buyer savings exactly equal to taxes, max debt ratio exactly met.

### 6.5 Security
- No external inputs used in shell or database operations without sanitization.
- No secrets or credentials committed to the repository.

---

## 7. Concrete Examples

### 7.1 Belgium (default) — minimal input, all parameters auto-resolved

**User provides only:**

| Parameter | Value |
|---|---|
| Property price | 350,000 EUR |
| Available savings | 80,000 EUR |
| Monthly net income | 6,000 EUR |
| Optimization preference | `minimize_total_cost` |

**Auto-resolved (country defaults to `BE`):**

| Parameter | Source | Value |
|---|---|---|
| Country | system default | `BE` |
| Profile quality | system default | `average` |
| Purchase taxes | estimated (12.5% of price) | ~43,750 EUR |
| Annual interest rate | BE average profile | 3.20% |
| Insurance rate | BE average profile | 0.25% /year |
| Max debt ratio | BE profile | 35% |
| Max loan duration | BE profile | 300 months (25 years) |
| Max monthly payment | system default | 2,200 EUR |

**Derived constraints:**
- Total acquisition cost = 350,000 + 43,750 = 393,750 EUR
- Minimum down payment = 393,750 × 20% = 78,750 EUR
- Binding monthly cap = min(6,000 × 35%, 2,200) = min(2,100, 2,200) = 2,100 EUR
- Loan range: 313,750 EUR (min, if all savings used as down payment) to 315,000 EUR (max, at minimum down payment)

The simulator returns the `(down_payment, duration)` pair that minimizes total interest + insurance cost while respecting all constraints.

### 7.2 France — purchase taxes provided explicitly (e.g. notary quote known)

| Parameter | Value |
|---|---|
| Property price | 499,000 EUR |
| Country | `FR` |
| Purchase taxes | 68,000 EUR _(user-supplied, overrides estimate)_ |
| Available savings | 100,000 EUR |
| Monthly net income | 5,500 EUR |
| Optimization preference | `minimize_total_cost` |

**Auto-resolved from France profile:**

| Parameter | Source | Value |
|---|---|---|
| Profile quality | system default | `average` |
| Annual interest rate | FR average profile | 3.50% |
| Insurance rate | FR average profile | 0.30% /year |
| Max debt ratio | FR profile | 35% |
| Max loan duration | FR profile | 300 months (25 years) |
| Taxes financeable | FR profile | No |
| Max monthly payment | system default | 2,200 EUR |

- Total acquisition cost = 567,000 EUR
- Minimum down payment = 68,000 EUR (taxes not financeable)
- Binding monthly cap = min(5,500 × 35%, 2,200) = min(1,925, 2,200) = 1,925 EUR
- Loan range: 467,000 EUR to 499,000 EUR

---

## 8. Out of Scope (v1)

- Variable / adjustable interest rates
- Automatic background polling of rates (online fetch is user-triggered only)
- Multi-borrower (co-borrower) scenarios
- User authentication and accounts
- Persistent storage / database
- Multi-currency support
- Bridge loans (prêt relais)
- PTZ (Prêt à Taux Zéro) or state-subsidized loan blending

---

## 9. Open Questions

| # | Question | Owner | Status |
|---|---|---|---|
| 1 | Should the insurance rate be fixed or decrease over time as the outstanding balance reduces? | @alahaouas | **Closed** — fixed rate applied to the original principal throughout the loan life |
| 2 | Should the simulator expose a CLI, a REST API, or a web UI? | @alahaouas | **Closed** — CLI |
| 3 | What is the target language/runtime? | @alahaouas | **Closed** — Python 3.11+; `decimal` module for fixed-point arithmetic, `rich` for terminal output, `click` for CLI |
| 4 | Should bank arrangement fees (frais de dossier) be factored into the APR calculation? | @alahaouas | **Closed** — no |
| 5 | Should the optimization step for down payment be configurable, or fixed at 1,000 in the local currency? | @alahaouas | **Closed** — fixed at 1,000 in the country currency |
| 6 | How should country profile values be updated over time (static file, admin endpoint, periodic release)? | @alahaouas | **Closed** — static file, updated manually |
| 7 | Should the system warn when user-supplied rates differ significantly from the country profile defaults? | @alahaouas | **Closed** — no warnings |
| 8 | Should sub-national variations be supported (e.g. Belgian region tax rates, US state closing costs, German Grunderwerbsteuer by Bundesland)? | @alahaouas | **Closed** — not needed, national level only |
| 9 | What online data source(s) should be used for the online profile fetch? (central bank APIs, financial data aggregators, specific websites) | @alahaouas | **Closed** — ECB Data Portal API for Eurozone; Bank of England for GB; FRED for US (see §5.4 data source table) |
| 10 | Should fetched rates require explicit user confirmation before being applied, or be applied automatically? | @alahaouas | **Closed** — auto-apply unless the user has already manually overridden the rate in the current session, in which case confirm before replacing |
| 11 | Should the online fetch target `average` rates, `best` rates, or both — and how does the source distinguish between them? | @alahaouas | **Closed** — `average` only; central banks publish population-average new-business rates; best/competitive rates are not available from any public API and must be set manually |
