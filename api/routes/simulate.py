"""POST /api/simulate — run a credit simulation and return the result."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from credit_simulator.calculator import build_amortization_schedule
from credit_simulator.optimizer import analyze_sweet_spot, optimize
from credit_simulator.profiles import SessionProfileStore
from credit_simulator.resolver import InfeasibleError, UserInputs, check_feasibility, resolve

from ..auth import optional_user
from ..db import get_db
from ..models import SimulateRequest
from ..serializers import to_json_safe

router = APIRouter()


def _d(v: str | None) -> Decimal | None:
    return Decimal(v) if v is not None else None


@router.post("/simulate", summary="Run a credit simulation")
def run_simulate(
    req: SimulateRequest,
    user_id: str | None = Depends(optional_user),
    db=Depends(get_db),
) -> dict:
    """Run the full simulation pipeline and return the optimised loan plan.

    Request body fields and their constraints are described in `docs/api.md`.

    Returns a JSON object with three keys:
    - `result`     — optimised loan plan (always present)
    - `sweet_spot` — down-payment sweet-spot analysis (present when `include_sweet_spot=true`)
    - `schedule`   — full amortization schedule (present when `include_schedule=true`)

    All monetary and rate values are returned as decimal strings to prevent
    IEEE-754 float precision loss in transit.
    """
    inputs = UserInputs(
        property_price=Decimal(req.property_price),
        monthly_net_income=Decimal(req.monthly_net_income),
        available_savings=Decimal(req.available_savings),
        country=req.country,
        profile_quality=req.profile_quality,  # type: ignore[arg-type]
        purchase_taxes=_d(req.purchase_taxes),
        annual_interest_rate=_d(req.annual_interest_rate),
        insurance_rate=_d(req.insurance_rate),
        min_down_payment_ratio=_d(req.min_down_payment_ratio),
        max_loan_duration_months=req.max_loan_duration_months,
        fixed_loan_duration_months=req.fixed_loan_duration_months,
        max_debt_ratio=_d(req.max_debt_ratio),
        max_monthly_payment=_d(req.max_monthly_payment),
        preferred_down_payment=_d(req.preferred_down_payment),
        optimization_preference=req.optimization_preference,
        opportunity_cost_rate=_d(req.opportunity_cost_rate),
    )

    store = SessionProfileStore()

    try:
        params = resolve(inputs, store)
        check_feasibility(params)
        result = optimize(params)
    except InfeasibleError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    response: dict = {"result": to_json_safe(result)}

    if req.include_sweet_spot:
        sweet_spot = analyze_sweet_spot(params)
        response["sweet_spot"] = to_json_safe(sweet_spot)
    else:
        response["sweet_spot"] = None

    if req.include_schedule:
        schedule = build_amortization_schedule(
            result.loan_principal,
            result.plan.annual_interest_rate,
            result.plan.annual_insurance_rate,
            result.loan_duration_months,
        )
        response["schedule"] = [to_json_safe(row) for row in schedule]
    else:
        response["schedule"] = None

    if user_id is not None and db is not None:
        db.table("simulations").insert({
            "user_id": user_id,
            "inputs": req.model_dump(exclude_none=True, mode="json"),
            "result": response["result"],
            "schedule": response.get("schedule"),
        }).execute()

    return response
