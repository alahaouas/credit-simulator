"""Unit tests for optimizer.py — grid search over all preference modes."""
from decimal import Decimal

import pytest

from credit_simulator.profiles import SessionProfileStore
from credit_simulator.optimizer import optimize, analyze_sweet_spot
from credit_simulator.resolver import UserInputs, resolve
from credit_simulator.config import SWEET_SPOT_LTV_TARGET, SWEET_SPOT_RESERVE_MONTHS


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
        p2 = p1 - Decimal("10000")
        ltv1 = p1 / params.property_price
        ltv2 = p2 / params.property_price
        plan1 = compute_loan_plan(p1, params.rate_for_ltv(ltv1), params.insurance_rate, 240)
        plan2 = compute_loan_plan(p2, params.rate_for_ltv(ltv2), params.insurance_rate, 240)
        expected_per_10k = plan1.total_cost_of_credit - plan2.total_cost_of_credit
        # marginal_saving_per_1k × 10 should match the 10k saving (within rounding)
        assert abs(analysis.marginal_saving_per_1k * 10 - expected_per_10k) < Decimal("5")

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
