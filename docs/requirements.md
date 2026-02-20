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

| Field | Description | Constraints |
|---|---|---|
| `property_price` | Market price of the property | > 0 |
| `purchase_taxes` | Total purchase taxes and fees (notary, registration, agency) | >= 0 |
| `total_acquisition_cost` | Derived: `property_price + purchase_taxes` | Computed, not entered directly |

### 2.2 Loan Parameters

| Field | Description | Constraints |
|---|---|---|
| `annual_interest_rate` | Bank's nominal annual interest rate | > 0, typically 0.5%–10% |
| `insurance_rate` | Annual borrower insurance rate (assurance emprunteur) | >= 0 |
| `min_down_payment_ratio` | Minimum down payment as a fraction of total cost | >= 0%, typically >= 10% |
| `max_loan_duration_months` | Maximum acceptable loan duration | 12–360 months (1–30 years) |

> **Note**: Banks in France typically require the down payment to cover at least the purchase taxes (notary fees etc.) since those are not financeable. The minimum down payment is therefore at least equal to `purchase_taxes`.

### 2.3 Buyer Constraints

| Field | Description | Constraints |
|---|---|---|
| `monthly_net_income` | Buyer's total monthly net income | > 0 |
| `max_debt_ratio` | Maximum debt-to-income ratio allowed | > 0, typically <= 35% |
| `max_monthly_payment` | Optional hard cap on monthly installment | > 0 if provided |
| `available_savings` | Total savings available for down payment | >= 0 |

### 2.4 Optimization Preferences

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

### 4.1 Feasibility Check (pre-optimization)

Before optimizing, the system shall verify:
1. `available_savings >= purchase_taxes` — taxes must be covered by the buyer (not financeable).
2. `monthly_net_income * max_debt_ratio >= minimum_possible_monthly_payment` — the buyer can afford any loan at all.
3. The required loan amount does not exceed bank limits.

If any check fails, the system must return an **ineligibility result** with a clear, specific reason.

### 4.2 Optimization Algorithm

Given the buyer's preference, the system shall search over the space of:
- Down payment amounts: from `purchase_taxes` up to `available_savings` (step: 1,000 EUR or configurable)
- Loan durations: from 12 months up to `max_loan_duration_months` (step: 12 months)

For each `(down_payment, duration)` pair, compute the resulting plan and check all constraints:
- `debt_ratio <= max_debt_ratio`
- `monthly_installment <= max_monthly_payment` (if set)
- `loan_principal > 0`

Among all **feasible** plans, select the one that best satisfies the declared preference.

### 4.3 EMI Formula

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

## 6. Concrete Example

| Parameter | Value |
|---|---|
| Property price | 499,000 EUR |
| Purchase taxes | 68,000 EUR |
| Total acquisition cost | 567,000 EUR |
| Annual interest rate | 3.5% |
| Insurance rate | 0.30% /year |
| Available savings | 100,000 EUR |
| Monthly net income | 5,500 EUR |
| Max debt ratio | 35% |
| Optimization preference | `minimize_total_cost` |

**Expected constraints**:
- Minimum down payment = 68,000 EUR (covers taxes)
- Maximum monthly payment = 5,500 × 35% = 1,925 EUR
- Loan range: 467,000 EUR (min) to 499,000 EUR (max, if savings only cover taxes)

The simulator should return the `(down_payment, duration)` pair that minimizes total interest + insurance cost while respecting all constraints.

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
| 5 | Should the optimization step for down payment be configurable, or fixed at 1,000 EUR? | @alahaouas | Open |
