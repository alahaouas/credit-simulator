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
    SWEET_SPOT_LTV_TARGET, SWEET_SPOT_RESERVE_MONTHS, SWEET_SPOT_OPPORTUNITY_COST_RATE,
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

    # Effective monthly cap = stricter of DTI limit and absolute payment cap (§4.2).
    effective_cap = min(
        params.monthly_net_income * params.max_debt_ratio,
        params.max_monthly_payment,
    )

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

        ltv = principal / params.property_price
        effective_rate = params.rate_for_ltv(ltv)

        duration_candidates = [params.fixed_loan_duration_months]
        for duration in duration_candidates:
            plan = compute_loan_plan(
                principal,
                effective_rate,
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
    ltv_ratio: Decimal        # principal / property_price
    dti_ratio: Decimal        # monthly_installment / monthly_net_income
    savings_remaining: Decimal
    is_sweet_spot: bool
    effective_rate: Decimal   # LTV-adjusted annual interest rate for this milestone


@dataclass(frozen=True)
class SweetSpotAnalysis:
    milestones: list              # list[SweetSpotMilestone], ordered by down_payment
    sweet_spot_reason: str        # human-readable explanation
    reserve_warning: str          # non-empty when min down payment already exceeds reserve
    duration_months: int
    # Marginal economics (constant across all down-payment levels for a fixed-rate loan)
    marginal_saving_per_1k: Decimal   # total cost saved per extra €1 000 of down payment
    effective_annual_yield: Decimal   # IRR of the down payment ≈ loan APR
    opportunity_cost_rate: Decimal    # benchmark annual rate used for comparison
    down_payment_is_efficient: bool   # True when mortgage yield > opportunity cost


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


def analyze_sweet_spot(
    params: ResolvedParams,
    opportunity_cost_rate: Optional[Decimal] = None,
) -> SweetSpotAnalysis:
    """Compute down-payment milestones and identify the objective sweet spot.

    For a fixed-rate mortgage the marginal interest saving per extra €1 000 of
    down payment is **constant** (= loan APR × annuity factor).  There is no
    mathematical diminishing-return curve — the sweet spot is therefore defined
    by opportunity cost:

      • If loan APR > opportunity cost rate → maximise down payment (up to the
        6-month income reserve ceiling).  The mortgage "pays" more than you can
        earn elsewhere.

      • If loan APR ≤ opportunity cost rate → use the minimum required down
        payment and invest the surplus.  You can beat the mortgage cost in the
        market.

    The LTV 80 % threshold is shown as a regulatory reference point (banks
    sometimes offer slightly better terms below it).

    Parameters
    ----------
    params:
        Resolved simulation parameters.
    opportunity_cost_rate:
        Override for testing; defaults to SWEET_SPOT_OPPORTUNITY_COST_RATE.
    """
    opp_rate = opportunity_cost_rate if opportunity_cost_rate is not None else SWEET_SPOT_OPPORTUNITY_COST_RATE

    duration = params.fixed_loan_duration_months
    candidates = _build_dp_candidates(params)

    def _milestone(dp: Decimal, label: str, is_sweet: bool = False) -> SweetSpotMilestone:
        principal = params.total_acquisition_cost - dp
        ltv = (principal / params.property_price).quantize(
            Decimal("0.0001"), rounding="ROUND_HALF_UP"
        )
        eff_rate = params.rate_for_ltv(ltv)
        plan = compute_loan_plan(principal, eff_rate, params.insurance_rate, duration)
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
            effective_rate=eff_rate,
        )

    # --- Determine effective floor for sweet-spot decision ---
    # If the minimum down payment falls in a surcharge LTV tier (rate_delta > 0),
    # anchoring the sweet spot there is irrational: a small extra amount exits the
    # penalty zone and delivers a return that dwarfs any opportunity-cost argument.
    # The effective floor is the cheapest down payment that puts the buyer in a
    # non-surcharge tier (rate_delta ≤ 0).
    min_dp = candidates[0]
    _min_principal = params.total_acquisition_cost - min_dp
    _min_ltv = _min_principal / params.property_price
    _min_rate_delta = ZERO
    for _t in sorted(params.ltv_rate_tiers, key=lambda t: t.ltv_max):
        if _min_ltv <= _t.ltv_max:
            _min_rate_delta = _t.rate_delta
            break
    effective_floor_dp = min_dp
    if _min_rate_delta > ZERO:
        # Find highest-LTV non-surcharge tier (cheapest to reach from above).
        _non_surcharge = [t for t in params.ltv_rate_tiers if t.rate_delta <= ZERO]
        if _non_surcharge:
            _nearest = max(_non_surcharge, key=lambda t: t.ltv_max)
            _exact = params.total_acquisition_cost - params.property_price * _nearest.ltv_max
            _floor_cand = (
                _exact / STEP_DOWN_PAYMENT
            ).to_integral_value(rounding="ROUND_CEILING") * STEP_DOWN_PAYMENT
            if _floor_cand <= params.available_savings:
                effective_floor_dp = _floor_cand

    # --- Marginal economics (computed at the effective floor) ---
    # Uses LTV-adjusted rates: the marginal saving is constant within a tier
    # but jumps at LTV tier crossings (where the rate itself drops).
    ref_principal = params.total_acquisition_cost - effective_floor_dp
    ref_ltv = ref_principal / params.property_price
    ref_rate = params.rate_for_ltv(ref_ltv)
    plan_ref = compute_loan_plan(ref_principal, ref_rate, params.insurance_rate, duration)
    alt_principal = ref_principal - Decimal("1000")
    alt_ltv = alt_principal / params.property_price
    alt_rate = params.rate_for_ltv(alt_ltv)
    plan_ref_minus1k = compute_loan_plan(alt_principal, alt_rate, params.insurance_rate, duration)
    marginal_saving_per_1k = (
        plan_ref.total_cost_of_credit - plan_ref_minus1k.total_cost_of_credit
    )
    effective_annual_yield = plan_ref.effective_annual_rate   # APR at effective floor LTV

    # --- Opportunity-cost decision ---
    down_payment_is_efficient = effective_annual_yield > opp_rate

    # --- 6-month reserve ceiling ---
    reserve_target = SWEET_SPOT_RESERVE_MONTHS * params.monthly_net_income
    reserve_ceiling_exact = params.available_savings - reserve_target
    reserve_dp: Decimal = candidates[0]
    for c in reversed(candidates):
        if c <= reserve_ceiling_exact:
            reserve_dp = c
            break

    # --- Sweet spot selection ---
    ltv_pct = int(SWEET_SPOT_LTV_TARGET * 100)
    opp_pct = f"{float(opp_rate) * 100:.1f}"
    yield_pct = f"{float(effective_annual_yield) * 100:.2f}"

    if down_payment_is_efficient:
        sweet_dp = reserve_dp
        reason = (
            f"Loan APR ({yield_pct}%) exceeds the reference rate ({opp_pct}%): "
            f"paying down the mortgage gives a better return than investing the "
            f"surplus. Maximise the down payment up to the {SWEET_SPOT_RESERVE_MONTHS}-month "
            f"income reserve ceiling — do not go further."
        )
    else:
        sweet_dp = effective_floor_dp
        if effective_floor_dp > candidates[0]:
            extra = effective_floor_dp - candidates[0]
            reason = (
                f"Loan APR ({yield_pct}%) is at or below the reference rate ({opp_pct}%): "
                f"investing the surplus could earn more than the mortgage interest saved. "
                f"However, the minimum down payment ({candidates[0]:,.0f} {params.currency}) "
                f"falls in an LTV surcharge tier — committing an extra "
                f"{extra:,.0f} {params.currency} immediately exits the penalty zone "
                f"and is almost always worth it regardless of opportunity cost. "
                f"Beyond this floor, invest any further surplus."
            )
        else:
            reason = (
                f"Loan APR ({yield_pct}%) is at or below the reference rate ({opp_pct}%): "
                f"investing the surplus earns more than it saves in mortgage interest. "
                f"Put only the minimum required down payment; every extra euro costs "
                f"you ({opp_pct}% − {yield_pct}%) in forgone returns."
            )

    # --- Reserve warning ---
    reserve_warning = ""
    if candidates[0] > reserve_ceiling_exact:
        reserve_warning = (
            f"Note: even the minimum down payment exceeds the {SWEET_SPOT_RESERVE_MONTHS}-month "
            f"income reserve ({reserve_target:,.0f} {params.currency}). "
            f"Ensure you have sufficient emergency funds before proceeding."
        )

    # --- LTV 80 % reference milestone ---
    ltv_dp: Optional[Decimal] = None
    for c in candidates:
        principal = params.total_acquisition_cost - c
        if principal / params.property_price <= SWEET_SPOT_LTV_TARGET:
            ltv_dp = c
            break

    # --- Build deduplicated, ordered milestone list ---
    spec: dict = {}   # Decimal -> (label, is_sweet)

    def _add(dp_val: Decimal, label: str, is_sweet: bool = False) -> None:
        if dp_val not in spec:
            spec[dp_val] = (label, is_sweet)
        elif is_sweet:
            spec[dp_val] = (label, True)

    _add(candidates[0], "Minimum")

    # Add milestones at every LTV tier crossing that improves the rate.
    # Tiers are sorted ascending by ltv_max; crossing tier[i].ltv_max downward
    # switches from tier[i+1] to tier[i], which is a rate improvement when
    # tier[i].rate_delta < tier[i+1].rate_delta.
    tiers = params.ltv_rate_tiers
    for i in range(len(tiers) - 1):
        tier, next_tier = tiers[i], tiers[i + 1]
        if tier.rate_delta >= next_tier.rate_delta:
            continue  # crossing this threshold does not improve the rate
        exact_dp = params.total_acquisition_cost - params.property_price * tier.ltv_max
        tier_dp = (exact_dp / STEP_DOWN_PAYMENT).to_integral_value(
            rounding="ROUND_CEILING"
        ) * STEP_DOWN_PAYMENT
        if params.min_down_payment < tier_dp < params.available_savings:
            _add(tier_dp, f"LTV≤{int(tier.ltv_max * 100)}% rate↓")

    if ltv_dp is not None and ltv_dp != candidates[0] and ltv_dp != candidates[-1]:
        _add(ltv_dp, f"LTV {ltv_pct}% (ref)")
    _add(sweet_dp, "★  Sweet spot", is_sweet=True)
    if reserve_dp != sweet_dp and reserve_dp != candidates[0] and reserve_dp != candidates[-1]:
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
        marginal_saving_per_1k=marginal_saving_per_1k,
        effective_annual_yield=effective_annual_yield,
        opportunity_cost_rate=opp_rate,
        down_payment_is_efficient=down_payment_is_efficient,
    )
