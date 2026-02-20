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

> **Note**: Whether purchase taxes are financeable by the bank is country-specific and defined in the country profile. For example, in France taxes are not financeable, so the minimum down payment always covers at least `purchase_taxes`.

### 2.3 Buyer Constraints

| Field | Description | Required | Constraints |
|---|---|---|---|
| `monthly_net_income` | Buyer's total monthly net income | Yes | > 0 |
| `available_savings` | Total savings available for down payment | Yes | >= 0 |
| `max_debt_ratio` | Maximum debt-to-income ratio | No | > 0; defaults to country profile value |
| `max_monthly_payment` | Hard cap on monthly installment | No | > 0; defaults to 2,200 EUR (or equivalent in country currency) |

### 2.4 Country Profiles

The system embeds a static reference table for each supported country. Each country has two **profile qualities**:

| Quality | Description |
|---|---|
| `average` _(default)_ | Typical market rates — represents what most borrowers obtain |
| `best` | Best competitive rates — represents the lowest rates available from top-tier lenders or brokers |

Profile quality only affects **market-driven fields** (`annual_interest_rate`, `insurance_rate`). Regulatory fields (purchase taxes, minimum down payment, maximum debt ratio, maximum duration) are identical across both qualities and cannot be set to "best" since they are fixed by law or banking regulation.

**Default country**: `BE` (Belgium) — used when `country` is not provided.

**Market-driven rates (vary by profile quality):**

| Country | Code | Currency | Avg Interest Rate | Best Interest Rate | Avg Insurance Rate | Best Insurance Rate |
|---|---|---|---|---|---|---|
| France | `FR` | EUR | 3.50% | 2.90% | 0.30% | 0.10% |
| Spain | `ES` | EUR | 3.50% | 2.80% | 0.20% | 0.09% |
| Germany | `DE` | EUR | 3.80% | 3.10% | 0.15% | 0.08% |
| Portugal | `PT` | EUR | 4.00% | 3.20% | 0.25% | 0.10% |
| Belgium _(default)_ | `BE` | EUR | 3.20% | 2.70% | 0.25% | 0.10% |
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
| `max_debt_ratio` | No | Default maximum debt-to-income ratio |
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
- Down payment amounts: from `min_down_payment` up to `available_savings` (step: 1,000 in the property currency, or configurable)
- Loan durations: from 12 months up to `max_loan_duration_months` (step: 12 months)

For each `(down_payment, duration)` pair, compute the resulting plan and check all constraints:
- `debt_ratio <= max_debt_ratio`
- `monthly_installment <= max_monthly_payment` (always enforced; defaults to 2,200 EUR)
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
- Insurance is added on top: `monthly_payment = EMI + (P × annual_insurance_rate / 12)`

> **Precision requirement**: all intermediate and final monetary values must use decimal fixed-point arithmetic. Floating-point types are forbidden for monetary computations.

---

## 5. Interactive Parameter Update Loop

After displaying simulation results, the system shall enter an interactive prompt that lets the user modify any input parameter and re-run the simulation without restarting the session.

### 5.1 Session Startup

At the start of a session, the system prompts for the three mandatory parameters that have no default:

| Parameter | Prompt |
|---|---|
| `property_price` | "Property price?" |
| `monthly_net_income` | "Monthly net income?" |
| `available_savings` | "Available savings?" |

All other parameters are optional at startup and resolved automatically (see section 2). Once the three mandatory values are collected, the system runs an initial simulation and displays the result before entering the update loop.

### 5.2 Behaviour

1. After each result is shown, the system prints the **current parameter values** (including which were user-set vs. auto-resolved from the country profile) and prompts the user to choose an action:
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
| Loan parameters | `annual_interest_rate`, `insurance_rate`, `min_down_payment_ratio`, `max_loan_duration_months` |
| Buyer constraints | `monthly_net_income`, `available_savings`, `max_debt_ratio`, `max_monthly_payment` |
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

The system can retrieve current market rates from an online source on demand, without the user having to enter values manually.

1. User selects "Update a country profile field" → "Fetch from online".
2. System asks: which country?
3. System asks: which quality to fetch? (`average`, `best`, or `both`)
4. System contacts the configured online data source and retrieves the latest market-driven rates (`annual_rate`, `insurance_rate`) for the selected country and quality.
5. System displays the fetched values alongside the current session values and asks for confirmation before applying.
6. On confirmation, values are applied exactly as in manual entry (step 6 above).
7. On rejection, no change is made and the prompt is re-shown.
8. If the online fetch fails (network error, source unavailable, data not found), the system displays a clear error and offers to fall back to manual entry.

> **Note**: Online fetch only retrieves market-driven fields (`annual_rate`, `insurance_rate`). Regulatory fields are not fetched — they must be updated manually.

---

**Updatable profile fields:**

| Field | Quality-sensitive | Manual | Online fetch | Validation |
|---|---|---|---|---|
| `annual_rate` | Yes (`average` / `best`) | Yes | Yes | > 0 |
| `insurance_rate` | Yes (`average` / `best`) | Yes | Yes | >= 0 |
| `purchase_tax_rate` | No (shared) | Yes | No | >= 0 |
| `taxes_financeable` | No (shared) | Yes | No | `true` or `false` |
| `min_down_payment_ratio` | No (shared) | Yes | No | 0%–100% |
| `max_debt_ratio` | No (shared) | Yes | No | > 0 |
| `max_loan_duration_months` | No (shared) | Yes | No | 12–600 |

> **Invariant**: `best` rates must always be ≤ the corresponding `average` rates. The system rejects any update (manual or fetched) that would violate this and displays an explicit error.

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
| 1 | Should the insurance rate be fixed or decrease over time as the outstanding balance reduces? | @alahaouas | Open |
| 2 | Should the simulator expose a CLI, a REST API, or a web UI? | @alahaouas | Open |
| 3 | What is the target language/runtime? | @alahaouas | Open |
| 4 | Should bank arrangement fees (frais de dossier) be factored into the APR calculation? | @alahaouas | Open |
| 5 | Should the optimization step for down payment be configurable, or fixed at 1,000 in the local currency? | @alahaouas | Open |
| 6 | How should country profile values be updated over time (static file, admin endpoint, periodic release)? | @alahaouas | **Closed** — static file, updated manually |
| 7 | Should the system warn when user-supplied rates differ significantly from the country profile defaults? | @alahaouas | **Closed** — no warnings |
| 8 | Should sub-national variations be supported (e.g. Belgian region tax rates, US state closing costs, German Grunderwerbsteuer by Bundesland)? | @alahaouas | **Closed** — not needed, national level only |
| 9 | What online data source(s) should be used for the online profile fetch? (central bank APIs, financial data aggregators, specific websites) | @alahaouas | Open |
| 10 | Should fetched rates require explicit user confirmation before being applied, or be applied automatically? | @alahaouas | Open |
| 11 | Should the online fetch target `average` rates, `best` rates, or both — and how does the source distinguish between them? | @alahaouas | Open |
