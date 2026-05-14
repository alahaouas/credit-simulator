# Runtime rate refresh — `credit-simulator rates`

Country mortgage rates are bundled with the package in `profiles.py` (see the
BE block dated **2026-05**). When market rates shift, you can override them at
runtime — without reinstalling or rebuilding the package — via the
`credit-simulator rates` subcommand group.

Overrides persist to the same `~/.credit_simulator/preferences.json` file the
interactive simulator already uses, so a subsequent simulator run automatically
picks them up via `preferences.apply_to_store`.

## Surface

```text
credit-simulator rates set    <COUNTRY> <FIELD> <VALUE>
credit-simulator rates show   [COUNTRY]
credit-simulator rates clear  <COUNTRY> [FIELD]
credit-simulator rates list
credit-simulator rates path
```

### Refreshable fields

| Field                     | Meaning                              |
|---------------------------|--------------------------------------|
| `annual_rate_average`     | Market-average annual interest rate  |
| `annual_rate_best`        | Best-profile annual interest rate    |
| `insurance_rate_average`  | Market-average annual insurance rate |
| `insurance_rate_best`     | Best-profile annual insurance rate   |

Regulatory fields (`purchase_tax_rate`, `max_debt_ratio`, `max_loan_duration_months`,
`min_down_payment_ratio`) are **not** refreshable via this command — they require
a code change.

### Validation

Set operations enforce the same invariants the interactive simulator does:

- `best ≤ average` for annual rates.
- `best ≤ average` for insurance rates.
- `COUNTRY` must be one of the supported country codes (see
  [docs/requirements.md](requirements.md#country-profiles)).

A value violating these is rejected with a non-zero exit code and an error
message; the persisted file is left unchanged.

## Examples

Refresh the Belgian best annual rate to 3.10%:

```pwsh
credit-simulator rates set BE annual_rate_best 0.0310
```

Inspect the effective rates after the override:

```pwsh
credit-simulator rates show BE
```

List every persisted override:

```pwsh
credit-simulator rates list
```

Clear a single field, or every override for a country:

```pwsh
credit-simulator rates clear BE annual_rate_best
credit-simulator rates clear BE
```

Locate the config file:

```pwsh
credit-simulator rates path
```

## Behavioural notes

- **Decimal format.** `VALUE` is parsed via `Decimal()`. Both `0.0310` and
  `0,0310` are accepted. Percent notation (`3.10%`) is **not** parsed; pass the
  raw decimal fraction.
- **Decimal precision.** Values round-trip exactly: `0.0320` stored is
  `Decimal("0.0320")` loaded.
- **Static fallback.** Clearing an override restores the bundled value for that
  field — there is no second-level fallback.
- **`last_updated_date`.** Currently reflects the bundled date only;
  `rates set` does **not** stamp a new date.  Future enhancement.
- **i18n.** The `rates` subcommands output English only; the interactive
  simulator remains EN/FR.

## Where this lives in the code

| File                              | Role                                     |
|-----------------------------------|------------------------------------------|
| [`src/credit_simulator/rate_cli.py`](../src/credit_simulator/rate_cli.py)        | Click subcommand group (`set`, `show`, `clear`, `list`, `path`) |
| [`src/credit_simulator/preferences.py`](../src/credit_simulator/preferences.py)  | `save_overrides_only()` writes the JSON; `apply_to_store()` restores it |
| [`src/credit_simulator/profiles.py`](../src/credit_simulator/profiles.py)        | `SessionProfileStore` enforces the `best ≤ average` invariant during `set` |
| [`tests/unit/test_rate_cli.py`](../tests/unit/test_rate_cli.py)                  | Unit tests for every subcommand          |
