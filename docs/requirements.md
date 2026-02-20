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

The system embeds a static reference table mapping each supported country code to its typical loan market parameters. These values are used as defaults when the corresponding input fields are omitted.

**Default country**: `BE` (Belgium) — used when `country` is not provided.

| Country | Code | Currency | Typical Interest Rate | Insurance Rate | Purchase Tax Rate | Min Down Payment | Max Debt Ratio | Max Duration |
|---|---|---|---|---|---|---|---|---|
| France | `FR` | EUR | 3.50% | 0.30% | 7.5% of price (old) / 2.5% (new) | covers taxes (not financeable) | 35% | 25 years |
| Spain | `ES` | EUR | 3.50% | 0.20% | 8.0% of price (ITP resale) | 20% of price | 35% | 30 years |
| Germany | `DE` | EUR | 3.80% | 0.15% | 5.0% of price (avg Grunderwerbsteuer + notary) | 20% of price | 35% | 30 years |
| Portugal | `PT` | EUR | 4.00% | 0.25% | 7.0% of price (IMT + stamp + notary) | 10% of price (residents) | 35% | 30 years |
| Belgium _(default)_ | `BE` | EUR | 3.20% | 0.25% | 12.5% of price (registration, Wallonia/Brussels) | 20% of price | 35% | 25 years |
| Italy | `IT` | EUR | 4.00% | 0.20% | 4.0% of price (avg cadastral + notary) | 20% of price | 35% | 30 years |
| United Kingdom | `GB` | GBP | 5.00% | 0.25% | 3.0% of price (avg SDLT) | 10% of price | 35% | 35 years |
| United States | `US` | USD | 7.00% | 0.80% | 2.5% of price (avg closing costs) | 20% of price (conventional) | 43% | 30 years |

> **Disclaimer**: These are reference values representing typical market conditions. They are not real-time rates and do not constitute financial advice. Users are encouraged to provide actual bank-quoted rates for precise results.

**Profile fields per country:**

| Field | Description |
|---|---|
| `currency` | ISO 4217 currency code for monetary outputs |
| `typical_annual_rate` | Default `annual_interest_rate` when not provided |
| `typical_insurance_rate` | Default `insurance_rate` when not provided |
| `purchase_tax_rate` | Used to estimate `purchase_taxes` when not provided: `property_price × rate` |
| `taxes_financeable` | Boolean — whether purchase taxes can be included in the loan principal |
| `min_down_payment_ratio` | Default minimum down payment ratio when not provided |
| `max_debt_ratio` | Default maximum debt-to-income ratio when not provided |
| `max_loan_duration_months` | Default maximum loan duration when not provided |

### 2.5 Optimization Preferences

The buyer must express which objective to prioritize:

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

1. Load the country profile for the given `country` code. If the country is not supported, return an explicit error.
2. For each optional loan parameter (`annual_interest_rate`, `insurance_rate`, `min_down_payment_ratio`, `max_loan_duration_months`, `max_debt_ratio`): use the user-supplied value if provided, otherwise use the country profile default.
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

## 5. Non-Functional Requirements

### 5.1 Precision
- All monetary values use fixed-point / decimal arithmetic.
- Rounding: half-up, to 2 decimal places for display, full precision for intermediate steps.

### 5.2 Validation
- All inputs validated at the system boundary with explicit, descriptive error messages.
- Rejected values: non-positive prices, negative rates, durations outside 1–30 years, savings below taxes amount.

### 5.3 Performance
- Full optimization search over all `(down_payment, duration)` pairs must complete in under 1 second for a standard 30-year / 1,000 EUR step search space.
- Amortization schedule generation for a 30-year loan must complete in under 200 ms.

### 5.4 Testability
- Every calculation function (EMI, APR, amortization row, debt ratio) must have unit tests with known expected values.
- Optimizer must have integration tests covering each preference mode.
- Edge cases: zero insurance, minimum duration (12 months), buyer savings exactly equal to taxes, max debt ratio exactly met.

### 5.5 Security
- No external inputs used in shell or database operations without sanitization.
- No secrets or credentials committed to the repository.

---

## 6. Concrete Examples

### 6.1 Belgium (default) — minimal input, all parameters auto-resolved

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
| Purchase taxes | estimated (12.5% of price) | ~43,750 EUR |
| Annual interest rate | BE profile | 3.20% |
| Insurance rate | BE profile | 0.25% /year |
| Max debt ratio | BE profile | 35% |
| Max loan duration | BE profile | 300 months (25 years) |
| Max monthly payment | system default | 2,200 EUR |

**Derived constraints:**
- Total acquisition cost = 350,000 + 43,750 = 393,750 EUR
- Minimum down payment = 393,750 × 20% = 78,750 EUR
- Binding monthly cap = min(6,000 × 35%, 2,200) = min(2,100, 2,200) = 2,100 EUR
- Loan range: 313,750 EUR (min) to 306,250 EUR (max if all savings used)

The simulator returns the `(down_payment, duration)` pair that minimizes total interest + insurance cost while respecting all constraints.

### 6.2 France — purchase taxes provided explicitly (e.g. notary quote known)

| Parameter | Value |
|---|---|
| Property price | 499,000 EUR |
| Country | `FR` |
| Purchase taxes | 68,000 EUR _(user-supplied, overrides estimate)_ |
| Available savings | 100,000 EUR |
| Monthly net income | 5,500 EUR |
| Max monthly payment | 2,200 EUR _(user-supplied)_ |
| Optimization preference | `minimize_total_cost` |

**Auto-resolved from France profile:**

| Parameter | Source | Value |
|---|---|---|
| Annual interest rate | FR profile | 3.50% |
| Insurance rate | FR profile | 0.30% /year |
| Max debt ratio | FR profile | 35% |
| Max loan duration | FR profile | 300 months (25 years) |
| Taxes financeable | FR profile | No |

- Total acquisition cost = 567,000 EUR
- Minimum down payment = 68,000 EUR (taxes not financeable)
- Binding monthly cap = min(5,500 × 35%, 2,200) = min(1,925, 2,200) = 1,925 EUR
- Loan range: 467,000 EUR to 499,000 EUR

---

## 7. Out of Scope (v1)

- Variable / adjustable interest rates
- Real-time bank rate feeds
- Multi-borrower (co-borrower) scenarios
- User authentication and accounts
- Persistent storage / database
- Multi-currency support
- Bridge loans (prêt relais)
- PTZ (Prêt à Taux Zéro) or state-subsidized loan blending

---

## 8. Open Questions

| # | Question | Owner | Status |
|---|---|---|---|
| 1 | Should the insurance rate be fixed or decrease over time as the outstanding balance reduces? | @alahaouas | Open |
| 2 | Should the simulator expose a CLI, a REST API, or a web UI? | @alahaouas | Open |
| 3 | What is the target language/runtime? | @alahaouas | Open |
| 4 | Should bank arrangement fees (frais de dossier) be factored into the APR calculation? | @alahaouas | Open |
| 5 | Should the optimization step for down payment be configurable, or fixed at 1,000 in the local currency? | @alahaouas | Open |
| 6 | How should country profile values be updated over time (static file, admin endpoint, periodic release)? | @alahaouas | Open |
| 7 | Should the system warn when user-supplied rates differ significantly from the country profile defaults? | @alahaouas | Open |
| 8 | Should sub-national variations be supported (e.g. Belgian region tax rates, US state closing costs, German Grunderwerbsteuer by Bundesland)? | @alahaouas | Open |
