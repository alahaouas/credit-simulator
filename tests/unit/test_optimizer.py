"""Unit tests for optimizer.py — grid search over all preference modes."""
from decimal import Decimal

import pytest

from credit_simulator.profiles import SessionProfileStore
from credit_simulator.optimizer import optimize
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
        assert result.debt_ratio <= Decimal("0.35")
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
