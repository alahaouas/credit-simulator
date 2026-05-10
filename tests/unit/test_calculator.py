"""Unit tests for calculator.py — EMI, amortization, APR."""
from decimal import Decimal
from unittest import mock

import pytest

from credit_simulator.calculator import (
    build_amortization_schedule,
    compute_apr,
    compute_emi,
    compute_loan_plan,
    compute_monthly_insurance,
)

ZERO = Decimal("0")


class TestComputeEMI:
    @pytest.mark.parametrize("principal,annual_rate,months,expected", [
        # Known values computed with standard formula
        # P=100000, r=3.5%/12, n=240 → EMI ≈ 579.96
        (Decimal("100000"), Decimal("0.035"), 240, Decimal("579.96")),
        # P=200000, r=3.2%/12, n=300 → EMI ≈ 969.36
        (Decimal("200000"), Decimal("0.032"), 300, Decimal("969.36")),
        # P=500000, r=5.0%/12, n=360 → EMI ≈ 2684.11
        (Decimal("500000"), Decimal("0.050"), 360, Decimal("2684.11")),
    ])
    def test_standard_cases(self, principal, annual_rate, months, expected):
        result = compute_emi(principal, annual_rate, months)
        assert result == expected, f"EMI mismatch: got {result}, expected {expected}"

    def test_zero_interest(self):
        """Zero interest: EMI = P / n."""
        result = compute_emi(Decimal("120000"), ZERO, 120)
        assert result == Decimal("1000.00")

    def test_single_month(self):
        """One month: entire principal returned."""
        result = compute_emi(Decimal("1000"), Decimal("0.12"), 1)
        # EMI = 1000 * 0.01 * 1.01 / (1.01 - 1) = 1000 * 0.01 * 1.01 / 0.01 = 1010.00
        assert result == Decimal("1010.00")

    def test_invalid_duration(self):
        with pytest.raises(ValueError, match="duration_months"):
            compute_emi(Decimal("100000"), Decimal("0.035"), 0)

    def test_negative_principal(self):
        with pytest.raises(ValueError, match="principal"):
            compute_emi(Decimal("-1"), Decimal("0.035"), 120)

    def test_negative_annual_rate(self):
        with pytest.raises(ValueError, match="annual_rate"):
            compute_emi(Decimal("100000"), Decimal("-0.01"), 120)


class TestComputeMonthlyInsurance:
    def test_standard(self):
        # 200000 * 0.0025 / 12 = 41.67
        result = compute_monthly_insurance(Decimal("200000"), Decimal("0.0025"))
        assert result == Decimal("41.67")

    def test_zero_rate(self):
        result = compute_monthly_insurance(Decimal("300000"), ZERO)
        assert result == ZERO


class TestAmortizationSchedule:
    def _build(self, principal="100000", annual_rate="0.035", insurance_rate="0.002", months=12):
        return build_amortization_schedule(
            Decimal(principal), Decimal(annual_rate), Decimal(insurance_rate), months
        )

    def test_row_count(self):
        schedule = self._build(months=60)
        assert len(schedule) == 60

    def test_first_period(self):
        schedule = self._build()
        row = schedule[0]
        assert row.period == 1
        assert row.opening_balance == Decimal("100000")
        # interest = 100000 * 0.035/12 = 291.67
        assert row.interest_component == Decimal("291.67")

    def test_closing_balance_decreases(self):
        schedule = self._build(months=24)
        balances = [row.closing_balance for row in schedule]
        for i in range(len(balances) - 1):
            assert balances[i] >= balances[i + 1], "Balance should decrease monotonically"

    def test_final_closing_balance_is_zero(self):
        schedule = self._build(months=60)
        assert schedule[-1].closing_balance == ZERO

    def test_insurance_constant(self):
        """Insurance component must be the same for every row."""
        schedule = self._build()
        insurance_values = {row.insurance_component for row in schedule}
        assert len(insurance_values) == 1

    def test_opening_equals_previous_closing(self):
        schedule = self._build(months=24)
        for i in range(1, len(schedule)):
            assert schedule[i].opening_balance == schedule[i - 1].closing_balance

    def test_installment_components_sum(self):
        """monthly_installment = principal + interest + insurance for each row."""
        schedule = self._build()
        for row in schedule:
            expected = row.principal_component + row.interest_component + row.insurance_component
            assert row.monthly_installment == expected


class TestLoanPlan:
    def test_total_repaid_equals_principal_plus_cost(self):
        plan = compute_loan_plan(
            Decimal("200000"), Decimal("0.032"), Decimal("0.0025"), 300
        )
        assert plan.total_repaid == plan.loan_principal + plan.total_cost_of_credit

    def test_total_cost_of_credit(self):
        plan = compute_loan_plan(
            Decimal("100000"), Decimal("0.035"), Decimal("0.002"), 120
        )
        assert plan.total_cost_of_credit == plan.total_interest_paid + plan.total_insurance_paid

    def test_monthly_installment_equals_emi_plus_insurance(self):
        plan = compute_loan_plan(
            Decimal("150000"), Decimal("0.04"), Decimal("0.003"), 180
        )
        assert plan.monthly_installment == plan.monthly_emi + plan.monthly_insurance

    def test_apr_positive(self):
        plan = compute_loan_plan(
            Decimal("200000"), Decimal("0.035"), Decimal("0.0025"), 240
        )
        assert plan.effective_annual_rate > ZERO

    def test_zero_insurance_plan(self):
        plan = compute_loan_plan(
            Decimal("100000"), Decimal("0.05"), ZERO, 60
        )
        assert plan.monthly_insurance == ZERO
        assert plan.total_insurance_paid == ZERO

    def test_zero_interest_zero_insurance_apr_is_zero(self):
        """A zero-cost loan (no interest, no insurance) → APR = 0."""
        plan = compute_loan_plan(Decimal("60000"), ZERO, ZERO, 60)
        assert plan.effective_annual_rate == ZERO

    def test_zero_interest_with_insurance_apr_positive(self):
        """Insurance cost alone still produces a positive APR."""
        plan = compute_loan_plan(
            Decimal("100000"), ZERO, Decimal("0.003"), 120
        )
        assert plan.effective_annual_rate > ZERO

    def test_high_rate_plan_converges(self):
        """APR computation must converge even at high (15%) rates."""
        plan = compute_loan_plan(
            Decimal("200000"), Decimal("0.15"), Decimal("0.001"), 120
        )
        assert plan.effective_annual_rate > Decimal("0.14")

    def test_very_short_loan_single_period(self):
        """1-month loan: entire principal repaid in one installment."""
        plan = compute_loan_plan(Decimal("1000"), Decimal("0.12"), ZERO, 1)
        assert plan.total_repaid == plan.loan_principal + plan.total_cost_of_credit


class TestComputeAprDirect:
    """Direct unit tests for compute_apr boundary cases."""

    def test_zero_principal_returns_zero(self):
        assert compute_apr(ZERO, Decimal("500"), 120) == ZERO

    def test_zero_installment_returns_zero(self):
        assert compute_apr(Decimal("100000"), ZERO, 120) == ZERO

    def test_installment_matches_principal_one_period(self):
        """1-period: monthly_installment equals principal+interest; APR must be positive."""
        apr = compute_apr(Decimal("1000"), Decimal("1010"), 1)
        assert apr > ZERO

    @pytest.mark.parametrize("annual_rate", [
        Decimal("0.01"), Decimal("0.05"), Decimal("0.10"), Decimal("0.15"),
    ])
    def test_apr_roundtrip_close_to_nominal(self, annual_rate):
        """APR from compute_loan_plan should be within ±0.5% of stated nominal rate."""
        principal = Decimal("150000")
        plan = compute_loan_plan(principal, annual_rate, ZERO, 240)
        assert abs(plan.effective_annual_rate - annual_rate) < Decimal("0.005")

    @mock.patch("builtins.abs")
    def test_apr_handles_zero_division_error_in_loop(self, mock_abs):
        """ZeroDivisionError inside the Newton-Raphson loop is caught and APR converges safely."""
        mock_abs.side_effect = ZeroDivisionError("Simulated ZeroDivisionError")
        # Should complete without raising and return some Decimal value
        apr = compute_apr(Decimal("100000"), Decimal("1000"), 120)
        assert isinstance(apr, Decimal)
        mock_abs.assert_called()

    @mock.patch("builtins.abs")
    def test_apr_handles_invalid_operation_in_loop(self, mock_abs):
        """InvalidOperation inside the Newton-Raphson loop is caught and APR converges safely."""
        from decimal import InvalidOperation
        mock_abs.side_effect = InvalidOperation("Simulated InvalidOperation")
        # Should complete without raising and return some Decimal value
        apr = compute_apr(Decimal("100000"), Decimal("1000"), 120)
        assert isinstance(apr, Decimal)
        mock_abs.assert_called()
