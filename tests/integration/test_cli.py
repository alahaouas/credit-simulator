"""Integration tests for the CLI — full pipeline from inputs to result."""
from decimal import Decimal

import pytest
from click.testing import CliRunner

from credit_simulator.cli import main
from credit_simulator.optimizer import optimize
from credit_simulator.profiles import SessionProfileStore
from credit_simulator.resolver import UserInputs, resolve


# ──────────────────────────────────────────────────────────────────────────────
# Full pipeline tests (no CLI runner — direct function call)
# ──────────────────────────────────────────────────────────────────────────────

def _run_pipeline(preference: str = "balanced", **overrides):
    defaults = dict(
        property_price=Decimal("350000"),
        monthly_net_income=Decimal("6000"),
        available_savings=Decimal("80000"),
        optimization_preference=preference,
    )
    defaults.update(overrides)
    inputs = UserInputs(**defaults)
    store = SessionProfileStore()
    params = resolve(inputs, store)
    return optimize(params)


class TestBelgiumDefaultPipeline:
    """§7.1 Belgium example — all parameters auto-resolved."""

    def test_result_country_is_be(self):
        result = _run_pipeline("minimize_total_cost")
        assert result.country == "BE"

    def test_total_acquisition_cost(self):
        result = _run_pipeline("minimize_total_cost")
        # 350000 + 350000*12.5% = 350000 + 43750 = 393750
        assert result.total_acquisition_cost == Decimal("393750")

    def test_monthly_installment_within_cap(self):
        result = _run_pipeline("minimize_total_cost")
        # max_monthly_payment cap = 2200
        assert result.plan.monthly_installment <= Decimal("2200.01")  # tolerance for rounding

    def test_down_payment_within_savings(self):
        result = _run_pipeline("minimize_total_cost")
        assert result.down_payment <= Decimal("80000")


class TestAllPreferences:
    @pytest.mark.parametrize("pref", [
        "minimize_total_cost",
        "minimize_monthly_payment",
        "minimize_duration",
        "minimize_down_payment",
        "balanced",
    ])
    def test_each_preference_produces_result(self, pref):
        result = _run_pipeline(pref)
        assert result.plan is not None
        assert result.loan_principal > Decimal("0")
        assert result.loan_duration_months >= 12


class TestSessionProfileStoreOverride:
    def test_fetched_rate_applied(self):
        store = SessionProfileStore()
        # Manually set a different rate
        store.set_annual_rate("BE", "average", Decimal("0.04"), manual=True)
        inputs = UserInputs(
            property_price=Decimal("350000"),
            monthly_net_income=Decimal("6000"),
            available_savings=Decimal("80000"),
        )
        params = resolve(inputs, store)
        assert params.annual_interest_rate == Decimal("0.04")

    def test_best_rate_cannot_exceed_average(self):
        store = SessionProfileStore()
        with pytest.raises(ValueError, match="cannot exceed"):
            store.set_annual_rate("BE", "best", Decimal("0.99"), manual=True)

    def test_average_rate_cannot_be_below_best(self):
        store = SessionProfileStore()
        with pytest.raises(ValueError, match="cannot be lower"):
            store.set_annual_rate("BE", "average", Decimal("0.001"), manual=True)


class TestCLIRunner:
    """Smoke tests via Click test runner (non-interactive flag paths)."""

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Credit Simulator" in result.output or "credit" in result.output.lower()

    def test_full_run_via_args(self):
        runner = CliRunner()
        # Provide all mandatory args; input 'exit' to quit the interactive loop
        result = runner.invoke(
            main,
            [
                "--property-price", "350000",
                "--income", "6000",
                "--savings", "80000",
                "--country", "BE",
                "--quality", "average",
                "--preference", "minimize_total_cost",
            ],
            input="exit\n",
        )
        assert result.exit_code == 0
        assert "Loan" in result.output or "loan" in result.output.lower()

    def test_unsupported_country_error(self):
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "--property-price", "350000",
                "--income", "6000",
                "--savings", "80000",
                "--country", "ZZ",
            ],
            input="exit\n",
        )
        # Should surface an error message (not crash with unhandled exception)
        assert "ZZ" in result.output or "Unsupported" in result.output or result.exit_code != 0

    def test_insufficient_savings_shows_ineligible(self):
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "--property-price", "500000",
                "--income", "6000",
                "--savings", "1000",  # way too low
                "--country", "BE",
            ],
            input="exit\n",
        )
        assert result.exit_code == 0
        assert "Ineligible" in result.output or "savings" in result.output.lower()
