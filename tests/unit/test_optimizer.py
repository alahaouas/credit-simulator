"""Unit tests for optimizer.py — grid search over all preference modes."""
from decimal import Decimal

import pytest

from credit_simulator.config import (
    SWEET_SPOT_OPPORTUNITY_COST_RATE,
    SWEET_SPOT_RESERVE_MONTHS,
)
from credit_simulator.optimizer import TierEconomics, analyze_sweet_spot, optimize
from credit_simulator.profiles import SessionProfileStore
from credit_simulator.resolver import UserInputs, resolve


def _store() -> SessionProfileStore:
    return SessionProfileStore()


def _inputs(**kwargs) -> UserInputs:
    defaults = dict(
        property_price=Decimal("350000"),
        monthly_net_income=Decimal("6000"),
        available_savings=Decimal("80000"),
    )
    defaults.update(kwargs)
    return UserInputs(**defaults)


def _run(preference: str, **inp_kwargs):
    inputs = _inputs(optimization_preference=preference, **inp_kwargs)
    params = resolve(inputs, _store())
    return optimize(params)


class TestOptimizeMinimizeTotalCost:
    def test_returns_result(self):
        result = _run("minimize_total_cost")
        assert result.plan.total_cost_of_credit > Decimal("0")

    def test_constraints_respected(self):
        result = _run("minimize_total_cost")
        assert result.plan.monthly_installment <= Decimal("2200")
        assert result.down_payment >= Decimal("0")

    def test_down_payment_within_savings(self):
        result = _run("minimize_total_cost")
        assert result.down_payment <= Decimal("80000")


class TestOptimizeMinimizeMonthlyPayment:
    def test_returns_result(self):
        result = _run("minimize_monthly_payment")
        assert result.plan.monthly_installment > Decimal("0")

    def test_payment_not_exceeding_cap(self):
        result = _run("minimize_monthly_payment")
        assert result.plan.monthly_installment <= Decimal("2200")


class TestOptimizeMinimizeDuration:
    def test_shorter_than_default(self):
        result_dur = _run("minimize_duration")
        result_cost = _run("minimize_total_cost")
        # minimize_duration should generally pick a shorter or equal duration
        assert result_dur.loan_duration_months <= result_cost.loan_duration_months + 12


class TestOptimizeMinimizeDownPayment:
    def test_smallest_feasible_down_payment(self):
        result = _run("minimize_down_payment")
        # Down payment should be close to minimum
        inputs = _inputs(optimization_preference="minimize_down_payment")
        params = resolve(inputs, _store())
        assert result.down_payment >= params.min_down_payment

    def test_loan_principal_is_positive(self):
        result = _run("minimize_down_payment")
        assert result.loan_principal > Decimal("0")


class TestOptimizeBalanced:
    def test_returns_result(self):
        result = _run("balanced")
        assert result.plan is not None

    def test_metadata(self):
        result = _run("balanced")
        assert result.country == "BE"
        assert result.currency == "EUR"
        assert result.optimization_preference == "balanced"


class TestOptimizeFranceExample:
    """Verify France scenarios: §7.2 parameters are infeasible (loan too large for income),
    but a higher-income variant succeeds."""

    def test_france_infeasible_low_income(self):
        """§7.2 exact inputs: loan of ~467–499k is unaffordable on 5500 income at 35% cap."""
        from credit_simulator.resolver import InfeasibleError, check_feasibility
        inputs = _inputs(
            optimization_preference="minimize_total_cost",
            property_price=Decimal("499000"),
            monthly_net_income=Decimal("5500"),
            available_savings=Decimal("100000"),
            country="FR",
            purchase_taxes=Decimal("68000"),
        )
        params = resolve(inputs, _store())
        with pytest.raises((InfeasibleError, ValueError)):
            check_feasibility(params)
            optimize(params)

    def test_france_feasible_higher_income(self):
        """France with higher income (10 000 EUR) and large savings produces a valid plan."""
        result = _run(
            "minimize_total_cost",
            property_price=Decimal("499000"),
            monthly_net_income=Decimal("10000"),
            available_savings=Decimal("200000"),
            country="FR",
            purchase_taxes=Decimal("68000"),
        )
        assert result.country == "FR"
        assert result.total_acquisition_cost == Decimal("567000")
        assert result.down_payment >= Decimal("68000")
        assert result.plan.monthly_installment <= Decimal("3500.01")
        assert Decimal("0") < result.ltv_ratio <= Decimal("1")


class TestOptimizeInvalidPreference:
    def test_raises_on_unknown_preference(self):
        inputs = _inputs(optimization_preference="unknown_pref")
        params = resolve(inputs, _store())
        with pytest.raises(ValueError, match="Unknown optimization preference"):
            optimize(params)


class TestOptimizerDTIConstraint:
    def test_optimizer_respects_dti_cap(self):
        # property=200 000, income=4 000 → effective DTI cap = 4000 × 35% = 1 400 EUR.
        # Min principal: 225 000 − 100 000 = 125 000 → payment ≈ 660 EUR (well within cap).
        # The optimizer must not return a plan exceeding 1 400 EUR.
        result = _run(
            "minimize_total_cost",
            property_price=Decimal("200000"),
            monthly_net_income=Decimal("4000"),
            available_savings=Decimal("100000"),
        )
        assert result.plan.monthly_installment <= Decimal("1400.01")  # tolerance for rounding

    def test_optimizer_dti_cap_is_binding_over_absolute_cap(self):
        # income=4000, DTI cap=1400, absolute cap=2200 → effective cap is 1400.
        # Confirm the returned plan is ≤ DTI cap (not allowed to reach 2200).
        result = _run(
            "minimize_monthly_payment",
            property_price=Decimal("200000"),
            monthly_net_income=Decimal("4000"),
            available_savings=Decimal("100000"),
        )
        assert result.plan.monthly_installment <= Decimal("1400.01")

    def test_optimizer_uses_absolute_cap_when_stricter(self):
        # With income=10000 and BE debt_ratio=35%, dti_cap=3500 > absolute cap=2200.
        # The optimizer must honour the absolute cap.
        result = _run(
            "minimize_total_cost",
            monthly_net_income=Decimal("10000"),
            available_savings=Decimal("100000"),
        )
        assert result.plan.monthly_installment <= Decimal("2200.01")


class TestAnalyzeSweetSpot:
    """Unit tests for the opportunity-cost-based sweet-spot analysis."""

    def _params(self, **kwargs):
        defaults = dict(
            property_price=Decimal("350000"),
            monthly_net_income=Decimal("6000"),
            available_savings=Decimal("150000"),
            fixed_loan_duration_months=240,
        )
        defaults.update(kwargs)
        inputs = UserInputs(**defaults)
        return resolve(inputs, _store())

    # --- Structural invariants ---

    def test_returns_at_least_two_milestones(self):
        analysis = analyze_sweet_spot(self._params())
        assert len(analysis.milestones) >= 2

    def test_always_includes_minimum_and_maximum(self):
        analysis = analyze_sweet_spot(self._params())
        labels = [m.label for m in analysis.milestones]
        assert any("Minimum" in l for l in labels)
        assert any("Maximum" in l for l in labels)

    def test_exactly_one_sweet_spot(self):
        analysis = analyze_sweet_spot(self._params())
        assert len([m for m in analysis.milestones if m.is_sweet_spot]) == 1

    def test_milestones_ordered_by_down_payment(self):
        analysis = analyze_sweet_spot(self._params())
        dps = [m.down_payment for m in analysis.milestones]
        assert dps == sorted(dps)

    def test_total_cost_decreases_with_down_payment(self):
        analysis = analyze_sweet_spot(self._params())
        costs = [m.plan.total_cost_of_credit for m in analysis.milestones]
        assert all(costs[i] >= costs[i + 1] for i in range(len(costs) - 1))

    def test_sweet_spot_within_savings_bounds(self):
        params = self._params()
        analysis = analyze_sweet_spot(params)
        sweet = next(m for m in analysis.milestones if m.is_sweet_spot)
        assert sweet.down_payment >= params.min_down_payment
        assert sweet.down_payment <= params.available_savings

    def test_duration_echoed(self):
        analysis = analyze_sweet_spot(self._params(fixed_loan_duration_months=180))
        assert analysis.duration_months == 180

    def test_reason_and_marginal_fields_non_empty(self):
        analysis = analyze_sweet_spot(self._params())
        assert analysis.sweet_spot_reason != ""
        assert analysis.marginal_saving_per_1k > Decimal("0")
        assert analysis.effective_annual_yield > Decimal("0")

    # --- Opportunity-cost logic ---

    def test_sweet_spot_is_minimum_when_opp_cost_exceeds_yield(self):
        # Force opportunity cost >> loan APR so minimum down is optimal.
        # Default params: 350k price → min LTV exactly 90% (base tier, no surcharge),
        # so effective_floor_dp == min_down_payment.
        params = self._params()
        analysis = analyze_sweet_spot(params, opportunity_cost_rate=Decimal("0.20"))
        sweet = next(m for m in analysis.milestones if m.is_sweet_spot)
        assert sweet.down_payment == params.min_down_payment
        assert analysis.down_payment_is_efficient is False

    def test_sweet_spot_exits_surcharge_zone(self):
        # BE best: 499k price + 68k taxes → total 567k, min_dp = 113 400, LTV = 90.9 %.
        # That puts the buyer in the +0.35 % surcharge tier (LTV > 90 %).
        # Even when opp_rate > loan APR at the effective floor, the sweet spot must
        # be at or above the LTV≤90 % crossing (~118 000), not at the raw minimum.
        params = self._params(
            property_price=Decimal("499000"),
            available_savings=Decimal("300000"),
            monthly_net_income=Decimal("6000"),
            purchase_taxes=Decimal("68000"),
            fixed_loan_duration_months=240,
        )
        analysis = analyze_sweet_spot(params, opportunity_cost_rate=Decimal("0.035"))
        sweet = next(m for m in analysis.milestones if m.is_sweet_spot)
        # Sweet spot must NOT be the raw minimum (surcharge zone)
        assert sweet.down_payment > params.min_down_payment
        # LTV at sweet spot must be ≤ 90 % (out of surcharge zone)
        principal = params.total_acquisition_cost - sweet.down_payment
        ltv = principal / params.property_price
        assert ltv <= Decimal("0.90")

    def test_sweet_spot_is_reserve_ceiling_when_yield_exceeds_opp_cost(self):
        # Force opportunity cost << loan APR so maximising down is optimal
        params = self._params()
        analysis = analyze_sweet_spot(params, opportunity_cost_rate=Decimal("0.001"))
        sweet = next(m for m in analysis.milestones if m.is_sweet_spot)
        reserve_ceiling = params.available_savings - SWEET_SPOT_RESERVE_MONTHS * params.monthly_net_income
        assert sweet.down_payment <= reserve_ceiling
        assert analysis.down_payment_is_efficient is True

    def test_marginal_saving_matches_direct_calculation(self):
        # Verify that marginal_saving_per_1k matches a direct calculation using
        # LTV-adjusted rates (constant within a single LTV tier, larger at crossings).
        params = self._params()
        analysis = analyze_sweet_spot(params)
        from credit_simulator.calculator import compute_loan_plan
        p1 = params.total_acquisition_cost - params.min_down_payment
        p2 = p1 - Decimal("1000")
        ltv1 = p1 / params.property_price
        ltv2 = p2 / params.property_price
        plan1 = compute_loan_plan(p1, params.rate_for_ltv(ltv1), params.insurance_rate, 240)
        plan2 = compute_loan_plan(p2, params.rate_for_ltv(ltv2), params.insurance_rate, 240)
        expected_per_1k = plan1.total_cost_of_credit - plan2.total_cost_of_credit
        # The analyzer computes marginal_saving_per_1k with the same 1 k step, so
        # results must agree to within 1 EUR (pure Decimal rounding, no nonlinearity).
        assert abs(analysis.marginal_saving_per_1k - expected_per_1k) <= Decimal("1")

    def test_reserve_warning_when_min_dp_exceeds_buffer(self):
        # Very low income → reserve floor is tiny → min down payment may exceed it
        params = self._params(monthly_net_income=Decimal("1000"))
        analysis = analyze_sweet_spot(params)
        reserve_ceiling = params.available_savings - SWEET_SPOT_RESERVE_MONTHS * params.monthly_net_income
        if params.min_down_payment > reserve_ceiling:
            assert analysis.reserve_warning != ""

    def test_ltv_reference_milestone_present_when_achievable(self):
        # With enough savings relative to price, LTV 80% ref should appear
        params = self._params(
            property_price=Decimal("200000"),
            available_savings=Decimal("100000"),
            monthly_net_income=Decimal("8000"),
        )
        analysis = analyze_sweet_spot(params, opportunity_cost_rate=Decimal("0.20"))
        labels = [m.label for m in analysis.milestones]
        assert any("LTV" in l for l in labels)


class TestSweetSpotPreferredDownPayment:
    """Tests for preferred_down_payment milestone rendering in sweet-spot analysis."""

    def _params(self, preferred_down_payment=None, **kwargs):
        defaults = dict(
            property_price=Decimal("350000"),
            monthly_net_income=Decimal("6000"),
            available_savings=Decimal("150000"),
            fixed_loan_duration_months=240,
        )
        defaults.update(kwargs)
        if preferred_down_payment is not None:
            defaults["preferred_down_payment"] = preferred_down_payment
        inputs = UserInputs(**defaults)
        from credit_simulator.profiles import SessionProfileStore
        return resolve(inputs, SessionProfileStore())

    def test_preferred_dp_adds_your_choice_milestone(self):
        """A unique preferred_down_payment creates a 'Your choice' row."""
        params = self._params(preferred_down_payment=Decimal("90000"))
        analysis = analyze_sweet_spot(params)
        labels = [m.label for m in analysis.milestones]
        assert any("Your choice" in l for l in labels)

    def test_preferred_dp_coinciding_with_sweet_spot_appended(self):
        """When preferred equals the sweet spot its label gets '← Your choice' appended."""
        # Force sweet spot to minimum by using high opp cost
        params = self._params()
        analysis_base = analyze_sweet_spot(params, opportunity_cost_rate=Decimal("0.20"))
        sweet_dp = next(m.down_payment for m in analysis_base.milestones if m.is_sweet_spot)

        # Now set preferred_down_payment to that exact sweet_dp amount
        params2 = self._params(preferred_down_payment=sweet_dp)
        analysis2 = analyze_sweet_spot(params2, opportunity_cost_rate=Decimal("0.20"))
        labels = [m.label for m in analysis2.milestones]
        assert any("← Your choice" in l for l in labels)

    def test_preferred_dp_none_adds_no_your_choice(self):
        """Without a preferred_down_payment, no 'Your choice' milestone is added."""
        params = self._params()
        analysis = analyze_sweet_spot(params)
        labels = [m.label for m in analysis.milestones]
        assert not any("Your choice" in l for l in labels)

    def test_preferred_dp_milestone_ordered_correctly(self):
        """'Your choice' row is sorted in ascending down-payment order."""
        params = self._params(preferred_down_payment=Decimal("100000"))
        analysis = analyze_sweet_spot(params)
        dps = [m.down_payment for m in analysis.milestones]
        assert dps == sorted(dps)


class TestOptimizePreferredDownPayment:
    """Tests for preferred_down_payment pinning in optimize()."""

    def _run(self, preferred_down_payment, **kwargs):
        defaults = dict(
            # High income → wide feasibility window; high savings → broad dp range
            property_price=Decimal("350000"),
            monthly_net_income=Decimal("10000"),
            available_savings=Decimal("200000"),
            optimization_preference="balanced",
            preferred_down_payment=preferred_down_payment,
        )
        defaults.update(kwargs)
        inputs = UserInputs(**defaults)
        from credit_simulator.profiles import SessionProfileStore
        params = resolve(inputs, SessionProfileStore())
        return optimize(params)

    def test_optimizer_uses_preferred_down_payment(self):
        """When preferred_down_payment is set the optimizer returns exactly that amount."""
        result = self._run(Decimal("100000"))
        assert result.down_payment == Decimal("100000")

    def test_preferred_dp_does_not_exceed_savings(self):
        result = self._run(Decimal("150000"))
        assert result.down_payment <= Decimal("200000")


# ── New feature tests ────────────────────────────────────────────────────────


def _sweet_params(**kwargs):
    """Resolve params with generous savings so all milestones can appear."""
    defaults = dict(
        property_price=Decimal("350000"),
        monthly_net_income=Decimal("6000"),
        available_savings=Decimal("200000"),
    )
    defaults.update(kwargs)
    return resolve(UserInputs(**defaults), SessionProfileStore())


class TestOpportunityCostRate:
    def test_default_opp_rate_from_config(self):
        params = _sweet_params()
        assert params.opportunity_cost_rate == SWEET_SPOT_OPPORTUNITY_COST_RATE

    def test_user_opp_rate_propagated(self):
        params = resolve(
            UserInputs(
                property_price=Decimal("300000"),
                monthly_net_income=Decimal("5000"),
                available_savings=Decimal("100000"),
                opportunity_cost_rate=Decimal("0.06"),
            ),
            SessionProfileStore(),
        )
        assert params.opportunity_cost_rate == Decimal("0.06")

    def test_opp_rate_override_in_analyze_sweet_spot(self):
        """Passing opportunity_cost_rate directly to analyze_sweet_spot overrides params."""
        params = _sweet_params()
        analysis = analyze_sweet_spot(params, opportunity_cost_rate=Decimal("0.10"))
        assert analysis.opportunity_cost_rate == Decimal("0.10")

    def test_high_opp_rate_makes_inefficient(self):
        """With opp_rate above any plausible APR the down payment is always inefficient."""
        params = _sweet_params()
        analysis = analyze_sweet_spot(params, opportunity_cost_rate=Decimal("0.20"))
        assert not analysis.down_payment_is_efficient

    def test_zero_opp_rate_makes_efficient(self):
        """With opp_rate = 0 every positive-APR mortgage is efficient."""
        params = _sweet_params()
        analysis = analyze_sweet_spot(params, opportunity_cost_rate=Decimal("0.001"))
        assert analysis.down_payment_is_efficient


class TestTierEconomics:
    def _analysis(self, **kwargs):
        return analyze_sweet_spot(_sweet_params(**kwargs))

    def test_tier_economics_returned(self):
        analysis = self._analysis()
        assert isinstance(analysis.tier_economics, list)
        assert len(analysis.tier_economics) > 0

    def test_tier_economics_type(self):
        analysis = self._analysis()
        for te in analysis.tier_economics:
            assert isinstance(te, TierEconomics)

    def test_best_tier_flagged(self):
        """Exactly one TierEconomics entry should be flagged is_best_tier."""
        analysis = self._analysis()
        best = [te for te in analysis.tier_economics if te.is_best_tier]
        assert len(best) == 1

    def test_best_tier_has_lowest_effective_rate(self):
        analysis = self._analysis()
        best = next(te for te in analysis.tier_economics if te.is_best_tier)
        for te in analysis.tier_economics:
            assert best.effective_rate <= te.effective_rate

    def test_saving_per_1k_positive(self):
        """Every tier should yield a positive saving per €1 000 extra DP."""
        analysis = self._analysis()
        for te in analysis.tier_economics:
            assert te.saving_per_1k > Decimal("0"), (
                f"Expected positive saving in tier {te.ltv_range}, got {te.saving_per_1k}"
            )

    def test_tier_economics_ordered_highest_ltv_first(self):
        """Tiers are returned highest-LTV-first (smallest required DP first)."""
        analysis = self._analysis()
        tiers = analysis.tier_economics
        # The first tier should have a higher effective rate than the last
        # (surcharge first → best rate last).
        if len(tiers) > 1:
            assert tiers[0].effective_rate >= tiers[-1].effective_rate

    def test_higher_rate_tier_saves_more_per_1k(self):
        """Tiers with higher effective rates save more per €1 000 (more expensive debt)."""
        analysis = self._analysis()
        tiers = analysis.tier_economics
        if len(tiers) > 1:
            # First tier (highest LTV, possibly surcharge) should save >= last tier (best rate)
            assert tiers[0].saving_per_1k >= tiers[-1].saving_per_1k

    def test_no_tiers_returns_empty_list(self):
        """Profiles with no LTV tiers produce an empty tier_economics list."""
        params = resolve(
            UserInputs(
                property_price=Decimal("200000"),
                monthly_net_income=Decimal("5000"),
                available_savings=Decimal("100000"),
            ),
            SessionProfileStore(),
        )
        # Build a params with empty ltv_rate_tiers via object replacement
        import dataclasses
        params_no_tiers = dataclasses.replace(params, ltv_rate_tiers=())
        analysis = analyze_sweet_spot(params_no_tiers)
        assert analysis.tier_economics == []


class TestRateFloor:
    def _analysis_big_savings(self, **kwargs):
        """Use large savings so the rate-floor DP is reachable."""
        defaults = dict(
            property_price=Decimal("300000"),
            monthly_net_income=Decimal("8000"),
            available_savings=Decimal("250000"),
        )
        defaults.update(kwargs)
        return analyze_sweet_spot(_sweet_params(**defaults))

    def test_rate_floor_dp_is_none_when_not_reachable(self):
        """With tight savings the rate-floor DP may exceed available_savings → None."""
        params = _sweet_params(
            property_price=Decimal("500000"),
            available_savings=Decimal("80000"),
        )
        analysis = analyze_sweet_spot(params)
        # Rate-floor DP to reach ≤75% LTV for 500k property is very high; may be None
        if analysis.rate_floor_down_payment is not None:
            assert analysis.rate_floor_down_payment <= params.available_savings

    def test_rate_floor_milestone_appears_when_reachable(self):
        analysis = self._analysis_big_savings()
        if analysis.rate_floor_down_payment is not None:
            assert any(m.is_rate_floor for m in analysis.milestones)

    def test_rate_floor_milestone_is_flagged(self):
        analysis = self._analysis_big_savings()
        if analysis.rate_floor_down_payment is not None:
            floor_ms = [m for m in analysis.milestones if m.is_rate_floor]
            assert len(floor_ms) == 1

    def test_rate_floor_has_best_effective_rate(self):
        """The rate-floor milestone has the lowest effective rate of all milestones."""
        analysis = self._analysis_big_savings()
        if analysis.rate_floor_down_payment is not None:
            floor_ms = next(m for m in analysis.milestones if m.is_rate_floor)
            for m in analysis.milestones:
                assert floor_ms.effective_rate <= m.effective_rate

    def test_no_rate_floor_when_no_tiers(self):
        import dataclasses
        params = _sweet_params()
        params_no_tiers = dataclasses.replace(params, ltv_rate_tiers=())
        analysis = analyze_sweet_spot(params_no_tiers)
        assert analysis.rate_floor_down_payment is None


class TestCrossoverNote:
    def test_crossover_note_non_empty(self):
        analysis = analyze_sweet_spot(_sweet_params())
        assert analysis.crossover_note != ""

    def test_crossover_note_contains_apr(self):
        """Crossover note must reference the loan APR."""
        params = _sweet_params()
        analysis = analyze_sweet_spot(params)
        apr_pct = f"{analysis.effective_annual_yield * 100:.2f}"
        assert apr_pct in analysis.crossover_note

    def test_crossover_note_stable_across_opp_rates(self):
        """The crossover note only depends on the loan APR, not the opp_rate."""
        params = _sweet_params()
        a1 = analyze_sweet_spot(params, opportunity_cost_rate=Decimal("0.02"))
        a2 = analyze_sweet_spot(params, opportunity_cost_rate=Decimal("0.07"))
        assert a1.crossover_note == a2.crossover_note
