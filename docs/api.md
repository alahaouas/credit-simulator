# Credit Simulator API Reference

Base URL (local): `http://localhost:8000`
Interactive docs: `http://localhost:8000/api/docs`

---

## POST /api/simulate

Run the full simulation pipeline and return the optimised loan plan.

### Request body

All monetary and rate fields must be provided as **decimal strings** (e.g. `"300000"`,
`"0.035"`).  This prevents IEEE-754 float precision loss in transit.

#### Mandatory fields

| Field | Type | Description |
|---|---|---|
| `property_price` | string (decimal > 0) | Property purchase price |
| `monthly_net_income` | string (decimal > 0) | Buyer's net monthly income |
| `available_savings` | string (decimal > 0) | Total savings available for the purchase |

#### Optional property fields

| Field | Type | Default | Description |
|---|---|---|---|
| `country` | string | `"BE"` | ISO 3166-1 alpha-2 country code (`BE`, `FR`, `GB`, `US`) |
| `profile_quality` | `"average"` \| `"best"` | `"average"` | Rate quality profile |
| `purchase_taxes` | string (decimal ≥ 0) | computed from profile | Registration / notary taxes |

#### Optional loan parameter overrides

| Field | Type | Default | Description |
|---|---|---|---|
| `annual_interest_rate` | string (decimal ≥ 0) | from profile | Annual nominal interest rate (e.g. `"0.035"` = 3.5%) |
| `insurance_rate` | string (decimal ≥ 0) | from profile | Annual insurance rate applied to original principal |
| `min_down_payment_ratio` | string (decimal ≥ 0) | from profile | Minimum down-payment as a fraction of acquisition cost |
| `max_loan_duration_months` | integer | from profile | Maximum allowed loan term in months |
| `fixed_loan_duration_months` | integer | `240` (20 years) | Pin the optimizer to exactly this term |

#### Optional buyer constraint overrides

| Field | Type | Default | Description |
|---|---|---|---|
| `max_debt_ratio` | string (decimal ≥ 0) | from profile | Maximum debt-to-income ratio (e.g. `"0.33"`) |
| `max_monthly_payment` | string (decimal ≥ 0) | `"2200"` | Absolute monthly payment cap |
| `preferred_down_payment` | string (decimal ≥ 0) | none | Pin the optimizer to exactly this down payment |

#### Optimization

| Field | Type | Default | Description |
|---|---|---|---|
| `optimization_preference` | string | `"balanced"` | One of `balanced`, `minimize_total_cost`, `minimize_monthly_payment`, `minimize_duration`, `minimize_down_payment` |
| `opportunity_cost_rate` | string (decimal ≥ 0) | `"0.035"` | Annual benchmark return used in the sweet-spot analysis |

#### Response shaping

| Field | Type | Default | Description |
|---|---|---|---|
| `include_schedule` | boolean | `false` | Include the full month-by-month amortization schedule |
| `include_sweet_spot` | boolean | `true` | Include the down-payment sweet-spot analysis |

### Response

```json
{
  "result": {
    "down_payment": "60000.00",
    "loan_principal": "268800.00",
    "loan_duration_months": 240,
    "ltv_ratio": "0.8960",
    "country": "BE",
    "profile_quality": "average",
    "currency": "EUR",
    "monthly_net_income": "4000",
    "property_price": "300000",
    "purchase_taxes": "28800.00",
    "total_acquisition_cost": "328800.00",
    "optimization_preference": "balanced",
    "parameters_source": { "annual_interest_rate": "profile", ... },
    "plan": {
      "loan_principal": "268800.00",
      "annual_interest_rate": "0.033500",
      "annual_insurance_rate": "0.001800",
      "loan_duration_months": 240,
      "monthly_emi": "1540.12",
      "monthly_insurance": "40.32",
      "monthly_installment": "1580.44",
      "monthly_interest_first": "751.40",
      "total_interest_paid": "99629.88",
      "total_insurance_paid": "9676.80",
      "total_cost_of_credit": "109306.68",
      "total_repaid": "378106.68",
      "effective_annual_rate": "0.034995"
    }
  },
  "sweet_spot": {
    "milestones": [...],
    "sweet_spot_reason": "...",
    "reserve_warning": "",
    "duration_months": 240,
    "marginal_saving_per_1k": "...",
    "effective_annual_yield": "...",
    "opportunity_cost_rate": "0.035",
    "down_payment_is_efficient": true,
    "rate_floor_down_payment": "...",
    "tier_economics": [...],
    "crossover_note": "..."
  },
  "schedule": null
}
```

All monetary and rate values are **decimal strings**.  Parse with `Decimal(value)` on the
client side to preserve precision.

### Error responses

| HTTP status | Cause |
|---|---|
| `422 Unprocessable Entity` | Invalid input (bad decimal, missing field, unknown country, infeasible constraints) |
| `500 Internal Server Error` | Unexpected server error |

Error body:
```json
{ "detail": "human-readable error message" }
```

---

## Authentication

History endpoints require a Supabase JWT in the `Authorization` header:

```
Authorization: Bearer <supabase-access-token>
```

`POST /api/simulate` accepts the header optionally — without it the result is returned but not saved.

| Condition | Behaviour |
|---|---|
| No header | Anonymous — simulation runs, no persistence |
| Valid JWT | Authenticated — result saved to database |
| Invalid JWT | Treated as anonymous (silently) |
| Header present but `SUPABASE_URL` not set | `503 Service Unavailable` |
| No header on history endpoints | `401 Unauthorized` |

### Environment variables

| Variable | Purpose |
|---|---|
| `SUPABASE_URL` | Project URL (e.g. `https://xyz.supabase.co`) |
| `SUPABASE_SERVICE_ROLE_KEY` | Service-role secret key for server-side operations |

---

## GET /api/simulations

List the authenticated user's saved simulations, newest first.

### Response

```json
[
  {
    "id": "22222222-...",
    "created_at": "2026-05-11T10:00:00+00:00",
    "inputs": { "property_price": "300000", ... },
    "result": { "down_payment": "60000.00", ... }
  }
]
```

Schedule is not included in the list view.

### Error responses

| HTTP status | Cause |
|---|---|
| `401 Unauthorized` | Missing or invalid token |
| `503 Service Unavailable` | Supabase not configured |

---

## GET /api/simulations/{id}

Fetch a single simulation including the full schedule (if it was saved).

### Response

Same shape as the list item plus `"schedule": [...]` or `null`.

### Error responses

| HTTP status | Cause |
|---|---|
| `401 Unauthorized` | Missing or invalid token |
| `404 Not Found` | Simulation does not exist or belongs to another user |

---

## DELETE /api/simulations/{id}

Delete a simulation. Returns `204 No Content` on success.

### Error responses

| HTTP status | Cause |
|---|---|
| `401 Unauthorized` | Missing or invalid token |
| `404 Not Found` | Simulation does not exist or belongs to another user |

---

## Development

### Prerequisites

- Python 3.11+
- `pip`

### Install

```bash
# Core + API server (production-like)
pip install -e ".[web]"

# Core + API server + test/lint tooling (recommended for development)
pip install -e ".[dev]"
```

### Run the test suite

```bash
pytest
```

Coverage is printed automatically. The gate is **≥ 90%** on core modules.
To run only the API tests:

```bash
pytest tests/api/
```

### Lint

```bash
ruff check src/ tests/
```

### Start the API server

```bash
uvicorn api.main:app --reload --port 8000
```

The interactive Swagger UI is then available at `http://localhost:8000/api/docs`.

### Build a distributable wheel

```bash
pip install build
python -m build
```

The wheel is written to `dist/`.
