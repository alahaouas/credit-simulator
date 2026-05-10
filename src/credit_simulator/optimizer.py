"""Grid-search optimizer (§4.3).

Searches over down_payment candidates and selects the best feasible plan
according to the declared optimization preference.

Search space:
- down_payment: min_down_payment to available_savings, step 1 000 (country currency)
- duration: fixed to params.fixed_loan_duration_months (default 20 years)
  Duration grid-search is not yet implemented; use --duration to vary it.
"""
from __future__ import annotations

from dataclasses import dataclass, field as _field
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from .calculator import LoanPlan, compute_loan_plan
from .config import (
    STEP_DOWN_PAYMENT,
    SWEET_SPOT_LTV_TARGET,
    SWEET_SPOT_RESERVE_MONTHS,
    VALID_PREFERENCES,
    ZERO,
)
from .i18n import _
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
    """Return a sort key (lower is better) for the given plan.

    Note: 'minimize_duration' degrades to minimize_total_cost when the
    duration grid-search is disabled (single fixed duration).
    """
    tc = plan.total_cost_of_credit
    mp = plan.monthly_installment
    dp = down_payment

    if preference == "minimize_total_cost":
        return (tc, mp, dp)
    elif preference == "minimize_monthly_payment":
        return (mp, tc, -dp)
    elif preference == "minimize_duration":
        # Duration is constant across all candidates (grid-search not yet enabled).
        # Falls back to minimize_total_cost ordering.
        return (duration, tc, mp)
    elif preference == "minimize_down_payment":
        return (dp, tc, mp)
    else:  # balanced
        return (tc + mp * Decimal(duration), mp, dp)


def _build_dp_candidates(params: ResolvedParams) -> list:
    """Return the ordered list of down-payment amounts to evaluate.

    Starts from min_down_payment (exact), then steps in STEP_DOWN_PAYMENT
    increments up to available_savings (always included as the last entry).
    """
    dp = params.min_down_payment
    if dp % STEP_DOWN_PAYMENT != ZERO:
        dp_aligned = (dp // STEP_DOWN_PAYMENT + 1) * STEP_DOWN_PAYMENT
        candidates: list = [params.min_down_payment]
        dp = dp_aligned
    else:
        candidates = []
    while dp <= params.available_savings:
        candidates.append(dp)
        dp += STEP_DOWN_PAYMENT
    if not candidates or candidates[-1] < params.available_savings:
        candidates.append(params.available_savings)
    return candidates


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

    best_plan: LoanPlan | None = None
    best_down_payment = ZERO
    best_duration = 0
    best_score: tuple | None = None

    # If the user pinned a down payment, evaluate only that; otherwise grid-search.
    if params.preferred_down_payment is not None:
        candidates_dp = [params.preferred_down_payment]
    else:
        candidates_dp = _build_dp_candidates(params)

    for down_payment in candidates_dp:
        principal = params.total_acquisition_cost - down_payment
        if principal <= ZERO:
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
        Decimal("0.0001"), rounding=ROUND_HALF_UP
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
    is_rate_floor: bool = False    # True when this is the cheapest DP that hits the best rate
    is_user_choice: bool = False   # True when this matches the user's preferred_down_payment


@dataclass(frozen=True)
class TierEconomics:
    """Per-LTV-tier marginal economics of an extra €1 000 of down payment."""
    ltv_range: str            # e.g. "80%–90%"
    effective_rate: Decimal   # base_rate + tier.rate_delta
    rate_delta_label: str     # "+0.35%", "base", "−0.20%", "−0.30%"
    saving_per_1k: Decimal    # total credit-cost saved per €1 000 extra DP in this tier
    annual_yield: Decimal     # APR at this tier (≈ saving rate)
    is_best_tier: bool        # True for the tier with the lowest effective rate


@dataclass(frozen=True)
class SweetSpotAnalysis:
    milestones: list[SweetSpotMilestone]  # ordered by down_payment
    sweet_spot_reason: str        # human-readable explanation
    reserve_warning: str          # non-empty when min down payment already exceeds reserve
    duration_months: int
    # Marginal economics (at the effective floor)
    marginal_saving_per_1k: Decimal   # total cost saved per extra €1 000 of down payment
    effective_annual_yield: Decimal   # IRR of the down payment ≈ loan APR
    opportunity_cost_rate: Decimal    # benchmark annual rate used for comparison
    down_payment_is_efficient: bool   # True when mortgage yield > opportunity cost
    # Rate floor and per-tier breakdown
    rate_floor_down_payment: Decimal | None   # cheapest DP reaching the lowest-rate tier
    tier_economics: list[TierEconomics]       # per-tier breakdown (highest LTV first)
    crossover_note: str           # threshold explanation


def analyze_sweet_spot(
    params: ResolvedParams,
    opportunity_cost_rate: Decimal | None = None,
) -> SweetSpotAnalysis:
    """Compute down-payment milestones and identify the objective sweet spot.

    For a fixed-rate mortgage the marginal interest saving per extra €1 000 of
    down payment is constant within each LTV tier (= loan APR × annuity factor).
    The sweet spot is therefore defined by comparing the loan APR to the
    opportunity cost rate:

      • If loan APR > opportunity cost rate → maximise down payment (up to the
        6-month income reserve ceiling, capped at the rate floor if the best-tier
        APR falls back below the opportunity cost).

      • If loan APR ≤ opportunity cost rate → use the minimum required down
        payment and invest the surplus (but still exit LTV surcharge zones).

    Parameters
    ----------
    params:
        Resolved simulation parameters.
    opportunity_cost_rate:
        Override for testing; defaults to params.opportunity_cost_rate.
    """
    opp_rate = opportunity_cost_rate if opportunity_cost_rate is not None else params.opportunity_cost_rate

    duration = params.fixed_loan_duration_months
    candidates = _build_dp_candidates(params)

    def _milestone(
        dp: Decimal,
        label: str,
        is_sweet: bool = False,
        is_rf: bool = False,
        is_uc: bool = False,
    ) -> SweetSpotMilestone:
        principal = params.total_acquisition_cost - dp
        ltv = (principal / params.property_price).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        eff_rate = params.rate_for_ltv(ltv)
        plan = compute_loan_plan(principal, eff_rate, params.insurance_rate, duration)
        dti = (plan.monthly_installment / params.monthly_net_income).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
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
            is_rate_floor=is_rf,
            is_user_choice=is_uc,
        )

    # --- Determine effective floor for sweet-spot decision ---
    min_dp = candidates[0]
    _min_principal = params.total_acquisition_cost - min_dp
    _min_ltv = _min_principal / params.property_price
    _min_rate_delta = ZERO
    for _t in params.ltv_rate_tiers:
        if _min_ltv <= _t.ltv_max:
            _min_rate_delta = _t.rate_delta
            break
    effective_floor_dp = min_dp
    if _min_rate_delta > ZERO:
        _non_surcharge = [t for t in params.ltv_rate_tiers if t.rate_delta <= ZERO]
        if _non_surcharge:
            _nearest = max(_non_surcharge, key=lambda t: t.ltv_max)
            _exact = params.total_acquisition_cost - params.property_price * _nearest.ltv_max
            _floor_cand = (
                _exact / STEP_DOWN_PAYMENT
            ).to_integral_value(rounding=ROUND_CEILING) * STEP_DOWN_PAYMENT
            if _floor_cand <= params.available_savings:
                effective_floor_dp = _floor_cand

    # --- Rate floor: cheapest DP that reaches the lowest-rate LTV tier ---
    rate_floor_dp: Decimal | None = None
    if params.ltv_rate_tiers:
        _best_tier = min(params.ltv_rate_tiers, key=lambda t: t.rate_delta)
        _rf_exact = params.total_acquisition_cost - params.property_price * _best_tier.ltv_max
        if _rf_exact > params.min_down_payment:
            _rf_cand = (
                _rf_exact / STEP_DOWN_PAYMENT
            ).to_integral_value(rounding=ROUND_CEILING) * STEP_DOWN_PAYMENT
            if params.min_down_payment < _rf_cand <= params.available_savings:
                rate_floor_dp = _rf_cand

    # --- Marginal economics (computed at the effective floor) ---
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
    effective_annual_yield = plan_ref.effective_annual_rate

    # --- Per-tier economics ---
    tier_economics: list[TierEconomics] = []
    tiers_sorted = params.ltv_rate_tiers
    if tiers_sorted:
        min_delta = min(t.rate_delta for t in tiers_sorted)
        for i, tier in enumerate(tiers_sorted):
            lower_ltv = tiers_sorted[i - 1].ltv_max if i > 0 else ZERO
            upper_ltv = tier.ltv_max
            mid_ltv = (lower_ltv + upper_ltv) / 2
            p_mid = max(params.property_price * mid_ltv, Decimal("2000"))
            eff = params.annual_interest_rate + tier.rate_delta
            plan_mid = compute_loan_plan(p_mid, eff, params.insurance_rate, duration)
            plan_mid_m1 = compute_loan_plan(p_mid - Decimal("1000"), eff, params.insurance_rate, duration)
            tier_save = plan_mid.total_cost_of_credit - plan_mid_m1.total_cost_of_credit
            if tier.rate_delta == ZERO:
                delta_label = _("tier.base")
            elif tier.rate_delta > ZERO:
                delta_label = _(
                    "tier.surcharge", pct=f"{tier.rate_delta * 100:.2f}"
                )
            else:
                delta_label = _(
                    "tier.discount", pct=f"{abs(tier.rate_delta) * 100:.2f}"
                )
            lower_pct = int(lower_ltv * 100)
            upper_pct = int(upper_ltv * 100)
            ltv_range = f"≤{upper_pct}%" if lower_pct == 0 else f"{lower_pct}%–{upper_pct}%"
            tier_economics.append(TierEconomics(
                ltv_range=ltv_range,
                effective_rate=eff,
                rate_delta_label=delta_label,
                saving_per_1k=tier_save,
                annual_yield=plan_mid.effective_annual_rate,
                is_best_tier=(tier.rate_delta == min_delta),
            ))
        tier_economics.reverse()  # highest LTV first for display

    # --- Opportunity-cost decision ---
    down_payment_is_efficient = effective_annual_yield > opp_rate

    # When efficient at the floor, check whether efficiency reverses at the rate floor.
    # The best-tier APR may drop below the opportunity cost, making further increases
    # unprofitable. In that case cap the sweet spot at the rate floor, not the reserve.
    rate_floor_apr: Decimal | None = None
    rate_floor_efficient_boundary = False
    if down_payment_is_efficient and rate_floor_dp is not None:
        _rf_principal = params.total_acquisition_cost - rate_floor_dp
        _rf_ltv = _rf_principal / params.property_price
        _rf_rate = params.rate_for_ltv(_rf_ltv)
        _plan_rf = compute_loan_plan(_rf_principal, _rf_rate, params.insurance_rate, duration)
        rate_floor_apr = _plan_rf.effective_annual_rate
        if rate_floor_apr <= opp_rate:
            rate_floor_efficient_boundary = True

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
    opp_pct = f"{opp_rate * Decimal('100'):.1f}"
    yield_pct = f"{effective_annual_yield * Decimal('100'):.2f}"

    if down_payment_is_efficient:
        if rate_floor_efficient_boundary:
            # Efficient up to rate floor but best-tier APR dips below opp_rate.
            sweet_dp = rate_floor_dp  # type: ignore[assignment]
            rf_yield_pct = f"{rate_floor_apr * Decimal('100'):.2f}"  # type: ignore[operator]
            reason = _(
                "reason.efficient_capped_at_rate_floor",
                yield_pct=yield_pct,
                opp_pct=opp_pct,
                rf_yield_pct=rf_yield_pct,
            )
            sweet_label = _("milestone.sweet_spot_rate_floor")
        else:
            sweet_dp = reserve_dp
            reason = _(
                "reason.efficient",
                yield_pct=yield_pct,
                opp_pct=opp_pct,
                n=SWEET_SPOT_RESERVE_MONTHS,
            )
            sweet_label = _("milestone.sweet_spot")
    else:
        sweet_dp = effective_floor_dp
        sweet_label = _("milestone.sweet_spot")
        if effective_floor_dp > candidates[0]:
            extra = effective_floor_dp - candidates[0]
            reason = _(
                "reason.inefficient_exits_surcharge",
                yield_pct=yield_pct,
                opp_pct=opp_pct,
                min_dp=f"{candidates[0]:,.0f}",
                currency=params.currency,
                extra=f"{extra:,.0f}",
            )
        else:
            reason = _(
                "reason.inefficient_minimum",
                yield_pct=yield_pct,
                opp_pct=opp_pct,
            )

    # --- Crossover note ---
    crossover_note = _("crossover_note", yield_pct=yield_pct)

    # --- Reserve warning ---
    reserve_warning = ""
    if candidates[0] > reserve_ceiling_exact:
        reserve_warning = _(
            "reserve_warning",
            n=SWEET_SPOT_RESERVE_MONTHS,
            reserve=f"{reserve_target:,.0f}",
            currency=params.currency,
        )

    # --- LTV 80 % reference milestone ---
    ltv_dp: Decimal | None = None
    for c in candidates:
        principal = params.total_acquisition_cost - c
        if principal / params.property_price <= SWEET_SPOT_LTV_TARGET:
            ltv_dp = c
            break

    # --- Build deduplicated, ordered milestone list ---
    # spec maps down_payment → (label, is_sweet, is_rf, is_user_choice)
    spec: dict[Decimal, tuple[str, bool, bool, bool]] = {}

    def _add(
        dp_val: Decimal,
        label: str,
        is_sweet: bool = False,
        is_rf: bool = False,
        is_uc: bool = False,
    ) -> None:
        if dp_val not in spec:
            spec[dp_val] = (label, is_sweet, is_rf, is_uc)
        else:
            old_label, old_sweet, old_rf, old_uc = spec[dp_val]
            spec[dp_val] = (
                label if is_sweet else old_label,
                old_sweet or is_sweet,
                old_rf or is_rf,
                old_uc or is_uc,
            )

    _add(candidates[0], _("milestone.minimum"))

    for i in range(len(tiers_sorted) - 1):
        tier, next_tier = tiers_sorted[i], tiers_sorted[i + 1]
        if tier.rate_delta >= next_tier.rate_delta:
            continue
        exact_dp = params.total_acquisition_cost - params.property_price * tier.ltv_max
        tier_dp = (exact_dp / STEP_DOWN_PAYMENT).to_integral_value(
            rounding=ROUND_CEILING
        ) * STEP_DOWN_PAYMENT
        if params.min_down_payment < tier_dp < params.available_savings:
            _add(tier_dp, _("milestone.ltv_rate_cross", pct=int(tier.ltv_max * 100)))

    if ltv_dp is not None and ltv_dp != candidates[0] and ltv_dp != candidates[-1]:
        _add(ltv_dp, _("milestone.ltv_ref", pct=ltv_pct))

    if rate_floor_dp is not None:
        _add(rate_floor_dp, _("milestone.rate_floor"), is_rf=True)

    _add(sweet_dp, sweet_label, is_sweet=True)
    if reserve_dp != sweet_dp and reserve_dp != candidates[0] and reserve_dp != candidates[-1]:
        _add(reserve_dp, _("milestone.reserve_cap", n=SWEET_SPOT_RESERVE_MONTHS))
    _add(candidates[-1], _("milestone.maximum"))

    if params.preferred_down_payment is not None:
        pref = params.preferred_down_payment
        if pref in spec:
            old_label, old_sweet, old_rf, _uc = spec[pref]
            spec[pref] = (old_label + _("milestone.your_choice_suffix"), old_sweet, old_rf, True)
        else:
            spec[pref] = (_("milestone.your_choice"), False, False, True)

    milestones = [
        _milestone(dp, label, is_sweet, is_rf, is_uc)
        for dp, (label, is_sweet, is_rf, is_uc) in sorted(spec.items())
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
        rate_floor_down_payment=rate_floor_dp,
        tier_economics=tier_economics,
        crossover_note=crossover_note,
    )
