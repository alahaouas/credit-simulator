# Requirements — credit-simulator

## 1. Functional Requirements

### 1.1 Loan Simulation
- The system shall allow users to input a principal amount, interest rate, and loan term.
- The system shall compute the Equated Monthly Installment (EMI) based on the inputs.
- The system shall generate a full amortization schedule showing, for each period:
  - Payment number
  - Opening balance
  - Principal component
  - Interest component
  - Closing balance

### 1.2 Interest Rate Handling
- The system shall support fixed interest rates.
- The system shall support annual and monthly rate input formats, converting between them as needed.
- The system shall display the Annual Percentage Rate (APR) for any given loan configuration.

### 1.3 Loan Eligibility
- The system shall evaluate loan eligibility based on:
  - Credit score
  - Loan-to-Value (LTV) ratio
  - Debt-to-income ratio (if applicable)
- The system shall return a clear eligibility result (eligible / not eligible) with the reason for rejection when applicable.

### 1.4 Scenarios & Comparison
- The system shall allow users to define and compare multiple loan scenarios side by side.
- The system shall highlight the total cost (total interest paid) for each scenario.

---

## 2. Non-Functional Requirements

### 2.1 Precision
- All monetary calculations must use decimal/fixed-point arithmetic — floating-point types must not be used for currency values.
- Rounding must follow standard financial rounding rules (half-up).

### 2.2 Validation
- All user inputs must be validated at the system boundary.
- Invalid inputs (negative principal, zero or negative term, out-of-range interest rate) must return explicit, descriptive errors.

### 2.3 Performance
- Amortization schedule generation for a 30-year loan must complete in under 500 ms.

### 2.4 Testability
- Every calculation function must be covered by unit tests with known expected values.
- Edge cases must be tested: zero interest rate, single-period loan, maximum term, minimum principal.

### 2.5 Security
- No external inputs shall be used in shell commands or database queries without sanitization.
- No secrets or credentials shall be stored in source code or configuration files committed to the repository.

---

## 3. Out of Scope (v1)

- Real-time market rate feeds
- User authentication and accounts
- Persistent storage / database
- Multi-currency support

---

## 4. Open Questions

| # | Question | Owner | Status |
|---|---|---|---|
| 1 | Which interest rate models should be supported (flat rate, reducing balance, compound)? | @alahaouas | Open |
| 2 | Should the simulator expose a CLI, a REST API, or a web UI? | @alahaouas | Open |
| 3 | What is the target language/runtime? | @alahaouas | Open |
