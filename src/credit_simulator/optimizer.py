"""Grid-search optimizer (§4.3).

Searches over all (down_payment, duration) pairs and selects the best
feasible plan according to the declared optimization preference.

Search space:
- down_payment: min_down_payment to available_savings, step 1 000 (country currency)
- duration: 12 to max_loan_duration_months, step 12 months
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from .calculator import LoanPlan, compute_loan_plan
from .config import STEP_DOWN_PAYMENT, STEP_DURATION, VALID_PREFERENCES, ZERO
from .resolver import ResolvedParams


@dataclass(frozen=True)
class OptimizedResult:
    down_payment: Decimal
    loan_principal: Decimal
    loan_duration_months: int
    plan: LoanPlan
    ltv_ratio: Decimal
    # Echoed metadata
    country: str
    profile_quality: str
    currency: str
    monthly_net_income: Decimal
    property_price: Decimal
    purchase_taxes: Decimal
    total_acquisition_cost: Decimal
    optimization_preference: str
    parameters_source: dict[str, str]


def _score(
    preference: str,
    plan: LoanPlan,
    down_payment: Decimal,
    duration: int,
) -> tuple:
    """Return a sort key (lower is better) for the given plan."""
    tc = plan.total_cost_of_credit
    mp = plan.monthly_installment
    dp = down_payment

    if preference == "minimize_total_cost":
        return (tc, mp, dp)
    elif preference == "minimize_monthly_payment":
        return (mp, tc, -dp)
    elif preference == "minimize_duration":
        return (duration, tc, mp)
    elif preference == "minimize_down_payment":
        return (dp, tc, mp)
    else:  # balanced
        # Composite: normalize and sum — use ratios to keep comparable
        return (tc + mp * Decimal(duration), mp, dp)


def optimize(params: ResolvedParams) -> OptimizedResult:
    """Run the grid search and return the best feasible plan.

    Raises ValueError if no feasible plan exists in the search space.
    """
    preference = params.optimization_preference
    if preference not in VALID_PREFERENCES:
        raise ValueError(
            f"Unknown optimization preference '{preference}'. "
            f"Valid values: {', '.join(sorted(VALID_PREFERENCES))}"
        )

    effective_cap = params.max_monthly_payment

    best_plan: Optional[LoanPlan] = None
    best_down_payment = ZERO
    best_duration = 0
    best_score: Optional[tuple] = None

    # Build down payment grid: min_down_payment, min+1000, min+2000, … up to available_savings
    dp = params.min_down_payment
    # Round up to nearest 1000 if not already aligned
    if dp % STEP_DOWN_PAYMENT != ZERO:
        dp = (dp // STEP_DOWN_PAYMENT + 1) * STEP_DOWN_PAYMENT
        # Ensure we still include the exact min_down_payment as first candidate
        candidates_dp = [params.min_down_payment]
    else:
        candidates_dp = []

    while dp <= params.available_savings:
        candidates_dp.append(dp)
        dp += STEP_DOWN_PAYMENT

    # Always include available_savings as the last candidate (max down payment)
    if not candidates_dp or candidates_dp[-1] < params.available_savings:
        candidates_dp.append(params.available_savings)

    for down_payment in candidates_dp:
        principal = params.total_acquisition_cost - down_payment
        if principal <= ZERO:
            # Buyer pays cash — trivially feasible but unusual; skip (loan = 0)
            continue

        duration_candidates = (
            [params.fixed_loan_duration_months]
            if params.fixed_loan_duration_months is not None
            else range(STEP_DURATION, params.max_loan_duration_months + 1, STEP_DURATION)
        )
        for duration in duration_candidates:
            plan = compute_loan_plan(
                principal,
                params.annual_interest_rate,
                params.insurance_rate,
                duration,
            )

            # Constraint checks
            if plan.monthly_installment > effective_cap:
                continue

            score = _score(preference, plan, down_payment, duration)
            if best_score is None or score < best_score:
                best_score = score
                best_plan = plan
                best_down_payment = down_payment
                best_duration = duration

    if best_plan is None:
        raise ValueError(
            "No feasible loan plan found within the given constraints. "
            "Try increasing savings, income, or maximum duration."
        )

    principal = params.total_acquisition_cost - best_down_payment
    ltv_ratio = (principal / params.property_price).quantize(
        Decimal("0.0001"), rounding="ROUND_HALF_UP"
    )

    return OptimizedResult(
        down_payment=best_down_payment,
        loan_principal=principal,
        loan_duration_months=best_duration,
        plan=best_plan,
        ltv_ratio=ltv_ratio,
        country=params.country,
        profile_quality=params.profile_quality,
        currency=params.currency,
        monthly_net_income=params.monthly_net_income,
        property_price=params.property_price,
        purchase_taxes=params.purchase_taxes,
        total_acquisition_cost=params.total_acquisition_cost,
        optimization_preference=preference,
        parameters_source=dict(params.sources),
    )
