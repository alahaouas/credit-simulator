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
from .config import (
    STEP_DOWN_PAYMENT, STEP_DURATION, VALID_PREFERENCES, ZERO,
    SWEET_SPOT_LTV_TARGET, SWEET_SPOT_DTI_TARGET, SWEET_SPOT_RESERVE_MONTHS,
)
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


# ── Sweet-spot analysis ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SweetSpotMilestone:
    """One row in the sweet-spot comparison table."""
    label: str
    down_payment: Decimal
    loan_principal: Decimal
    plan: LoanPlan
    ltv_ratio: Decimal       # principal / property_price
    dti_ratio: Decimal       # monthly_installment / monthly_net_income
    savings_remaining: Decimal
    is_sweet_spot: bool


@dataclass(frozen=True)
class SweetSpotAnalysis:
    milestones: list          # list[SweetSpotMilestone], ordered by down_payment
    sweet_spot_reason: str    # human-readable explanation of how sweet spot was chosen
    reserve_warning: str      # non-empty if sweet spot drains the emergency fund
    duration_months: int


def _build_dp_candidates(params: ResolvedParams) -> list:
    """Same grid construction as optimize() — reused for sweet-spot analysis."""
    dp = params.min_down_payment
    if dp % STEP_DOWN_PAYMENT != ZERO:
        dp_aligned = (dp // STEP_DOWN_PAYMENT + 1) * STEP_DOWN_PAYMENT
        candidates = [params.min_down_payment]
        dp = dp_aligned
    else:
        candidates = []
    while dp <= params.available_savings:
        candidates.append(dp)
        dp += STEP_DOWN_PAYMENT
    if not candidates or candidates[-1] < params.available_savings:
        candidates.append(params.available_savings)
    return candidates


def analyze_sweet_spot(params: ResolvedParams) -> SweetSpotAnalysis:
    """Compute down-payment milestones and identify the sweet spot.

    Sweet spot = minimum down payment satisfying BOTH:
      - LTV ≤ SWEET_SPOT_LTV_TARGET (80 %)
      - DTI ≤ SWEET_SPOT_DTI_TARGET (35 % of net income)

    A 6-month income reserve marks the ceiling beyond which additional
    down payment drains the emergency fund for diminishing returns.
    """
    duration = (
        params.fixed_loan_duration_months
        if params.fixed_loan_duration_months is not None
        else params.max_loan_duration_months
    )
    candidates = _build_dp_candidates(params)

    def _milestone(dp: Decimal, label: str, is_sweet: bool = False) -> SweetSpotMilestone:
        principal = params.total_acquisition_cost - dp
        plan = compute_loan_plan(
            principal, params.annual_interest_rate, params.insurance_rate, duration
        )
        ltv = (principal / params.property_price).quantize(
            Decimal("0.0001"), rounding="ROUND_HALF_UP"
        )
        dti = (plan.monthly_installment / params.monthly_net_income).quantize(
            Decimal("0.0001"), rounding="ROUND_HALF_UP"
        )
        return SweetSpotMilestone(
            label=label,
            down_payment=dp,
            loan_principal=principal,
            plan=plan,
            ltv_ratio=ltv,
            dti_ratio=dti,
            savings_remaining=params.available_savings - dp,
            is_sweet_spot=is_sweet,
        )

    # --- Find threshold down payments ---
    ltv_pct = int(SWEET_SPOT_LTV_TARGET * 100)
    dti_pct = int(SWEET_SPOT_DTI_TARGET * 100)

    ltv_dp: Optional[Decimal] = None
    for c in candidates:
        principal = params.total_acquisition_cost - c
        if principal / params.property_price <= SWEET_SPOT_LTV_TARGET:
            ltv_dp = c
            break

    dti_dp: Optional[Decimal] = None
    for c in candidates:
        principal = params.total_acquisition_cost - c
        plan = compute_loan_plan(
            principal, params.annual_interest_rate, params.insurance_rate, duration
        )
        if plan.monthly_installment / params.monthly_net_income <= SWEET_SPOT_DTI_TARGET:
            dti_dp = c
            break

    # --- Determine sweet spot ---
    if ltv_dp is not None and dti_dp is not None:
        sweet_dp = max(ltv_dp, dti_dp)
        reason = (
            f"Minimum down payment clearing both LTV ≤ {ltv_pct}% and "
            f"monthly payment ≤ {dti_pct}% of income. Beyond this point each "
            f"extra €1 000 saves interest proportionally to the loan rate but "
            f"provides no additional threshold benefit."
        )
    elif ltv_dp is not None:
        sweet_dp = ltv_dp
        reason = (
            f"Minimum down payment clearing LTV ≤ {ltv_pct}% "
            f"(DTI ≤ {dti_pct}% is not achievable within your savings)."
        )
    elif dti_dp is not None:
        sweet_dp = dti_dp
        reason = (
            f"Minimum down payment where monthly payment ≤ {dti_pct}% of income "
            f"(LTV ≤ {ltv_pct}% is not achievable within your savings)."
        )
    else:
        sweet_dp = candidates[0]
        reason = (
            f"Neither LTV ≤ {ltv_pct}% nor DTI ≤ {dti_pct}% is achievable "
            f"within your savings — showing minimum feasible down payment."
        )

    # --- 6-month reserve ceiling ---
    reserve_target = SWEET_SPOT_RESERVE_MONTHS * params.monthly_net_income
    reserve_ceiling_exact = params.available_savings - reserve_target
    # Largest candidate that does not breach the reserve
    reserve_dp: Decimal = candidates[0]
    for c in reversed(candidates):
        if c <= reserve_ceiling_exact:
            reserve_dp = c
            break

    reserve_warning = ""
    if sweet_dp > reserve_ceiling_exact:
        reserve_warning = (
            f"Warning: reaching the sweet spot requires putting more than your "
            f"{SWEET_SPOT_RESERVE_MONTHS}-month income reserve "
            f"({reserve_target:,.0f} {params.currency}) would allow. "
            f"Consider stopping at the '{SWEET_SPOT_RESERVE_MONTHS}m buffer' row."
        )

    # --- Build deduplicated, ordered milestone list ---
    spec: dict = {}   # Decimal -> (label, is_sweet)

    def _add(dp_val: Decimal, label: str, is_sweet: bool = False) -> None:
        if dp_val not in spec:
            spec[dp_val] = (label, is_sweet)
        elif is_sweet:
            spec[dp_val] = (label, True)

    _add(candidates[0], "Minimum")
    if ltv_dp is not None and ltv_dp != sweet_dp:
        _add(ltv_dp, f"LTV {ltv_pct}% threshold")
    if dti_dp is not None and dti_dp != sweet_dp:
        _add(dti_dp, f"DTI {dti_pct}% threshold")
    _add(sweet_dp, "★  Sweet spot", is_sweet=True)
    if (
        reserve_dp != sweet_dp
        and reserve_dp != candidates[0]
        and reserve_dp != candidates[-1]
    ):
        _add(reserve_dp, f"{SWEET_SPOT_RESERVE_MONTHS}m reserve cap")
    _add(candidates[-1], "Maximum")

    milestones = [
        _milestone(dp, label, is_sweet)
        for dp, (label, is_sweet) in sorted(spec.items())
    ]

    return SweetSpotAnalysis(
        milestones=milestones,
        sweet_spot_reason=reason,
        reserve_warning=reserve_warning,
        duration_months=duration,
    )
