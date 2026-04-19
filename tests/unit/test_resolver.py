"""Unit tests for resolver.py — parameter resolution and feasibility."""
from decimal import Decimal

import pytest

from credit_simulator.profiles import SessionProfileStore
from credit_simulator.resolver import InfeasibleError, ResolvedParams, UserInputs, check_feasibility, resolve

ZERO = Decimal("0")


def _store() -> SessionProfileStore:
    return SessionProfileStore()


def _base_inputs(**kwargs) -> UserInputs:
    defaults = dict(
        property_price=Decimal("350000"),
        monthly_net_income=Decimal("6000"),
        available_savings=Decimal("80000"),
    )
    defaults.update(kwargs)
    return UserInputs(**defaults)


class TestResolveDefaults:
    def test_default_country_is_be(self):
        params = resolve(_base_inputs(), _store())
        assert params.country == "BE"

    def test_default_quality_is_average(self):
        params = resolve(_base_inputs(), _store())
        assert params.profile_quality == "average"

    def test_purchase_taxes_estimated_from_profile(self):
        params = resolve(_base_inputs(), _store())
        # BE purchase_tax_rate = 12.5%
        expected = Decimal("350000") * Decimal("0.125")
        assert params.purchase_taxes == expected.quantize(Decimal("0.01"))
        assert params.sources["purchase_taxes"] == "profile"

    def test_purchase_taxes_user_override(self):
        params = resolve(_base_inputs(purchase_taxes=Decimal("40000")), _store())
        assert params.purchase_taxes == Decimal("40000")
        assert params.sources["purchase_taxes"] == "user"

    def test_total_acquisition_cost(self):
        params = resolve(_base_inputs(), _store())
        assert params.total_acquisition_cost == params.property_price + params.purchase_taxes

    def test_loan_params_from_profile(self):
        params = resolve(_base_inputs(), _store())
        assert params.sources["annual_interest_rate"] == "profile"
        assert params.sources["insurance_rate"] == "profile"

    def test_loan_params_user_override(self):
        params = resolve(
            _base_inputs(annual_interest_rate=Decimal("0.04"), insurance_rate=Decimal("0.001")),
            _store(),
        )
        assert params.annual_interest_rate == Decimal("0.04")
        assert params.insurance_rate == Decimal("0.001")
        assert params.sources["annual_interest_rate"] == "user"

    def test_fr_taxes_not_financeable(self):
        params = resolve(_base_inputs(country="FR"), _store())
        assert params.taxes_financeable is False

    def test_fr_min_down_payment_equals_taxes_when_taxes_exceed_ratio(self):
        # FR: taxes not financeable, min_dp = max(purchase_taxes, total * 0%)
        # FR min_down_payment_ratio = 0.0 (must cover taxes)
        params = resolve(
            _base_inputs(country="FR", purchase_taxes=Decimal("68000")),
            _store(),
        )
        # min_dp = max(68000, 567000 * 0) = 68000
        assert params.min_down_payment == Decimal("68000")

    def test_unsupported_country(self):
        with pytest.raises(ValueError, match="Unsupported country"):
            resolve(_base_inputs(country="ZZ"), _store())


class TestFeasibility:
    def _params(self, **kwargs) -> ResolvedParams:
        return resolve(_base_inputs(**kwargs), _store())

    def test_feasible_passes(self):
        params = self._params()
        check_feasibility(params)  # should not raise

    def test_insufficient_savings(self):
        params = resolve(
            _base_inputs(available_savings=Decimal("1000")),  # way below min_dp
            _store(),
        )
        with pytest.raises(InfeasibleError, match="Insufficient savings"):
            check_feasibility(params)

    def test_monthly_payment_cap_exceeded(self):
        # Set an extremely low max_monthly_payment so that even the smallest loan is infeasible
        params = resolve(
            _base_inputs(
                max_monthly_payment=Decimal("1"),  # absurdly low cap
                available_savings=Decimal("100000"),
            ),
            _store(),
        )
        with pytest.raises(InfeasibleError, match="Monthly payment"):
            check_feasibility(params)

    def test_default_max_debt_ratio_from_profile(self):
        params = self._params()
        # BE profile max_debt_ratio = 35%
        assert params.max_debt_ratio == Decimal("0.35")

    def test_user_max_debt_ratio_overrides_profile(self):
        params = resolve(_base_inputs(max_debt_ratio=Decimal("0.28")), _store())
        assert params.max_debt_ratio == Decimal("0.28")
        assert params.sources["max_debt_ratio"] == "user"

    def test_us_max_debt_ratio_is_43_pct(self):
        params = resolve(_base_inputs(country="US"), _store())
        assert params.max_debt_ratio == Decimal("0.43")

    def test_dti_cap_is_stricter_than_absolute_cap(self):
        # Income=4000, debt_ratio=35% → dti cap=1400, absolute cap=2200
        # Effective cap must be 1400
        params = resolve(
            _base_inputs(monthly_net_income=Decimal("4000"), available_savings=Decimal("100000")),
            _store(),
        )
        from credit_simulator.config import DEFAULT_MAX_MONTHLY_PAYMENT
        effective_cap = min(params.monthly_net_income * params.max_debt_ratio, params.max_monthly_payment)
        assert effective_cap == Decimal("1400")
        assert effective_cap < DEFAULT_MAX_MONTHLY_PAYMENT

    def test_preferred_down_payment_below_minimum_raises(self):
        params = resolve(
            _base_inputs(preferred_down_payment=Decimal("1000")),
            _store(),
        )
        with pytest.raises(InfeasibleError, match="below the required minimum"):
            check_feasibility(params)

    def test_preferred_down_payment_above_savings_raises(self):
        params = resolve(
            _base_inputs(preferred_down_payment=Decimal("999999")),
            _store(),
        )
        with pytest.raises(InfeasibleError, match="exceeds available savings"):
            check_feasibility(params)

    def test_cash_purchase_is_feasible(self):
        """Buyer with savings >= total acquisition cost can pay cash; always feasible."""
        params = resolve(
            _base_inputs(
                property_price=Decimal("200000"),
                available_savings=Decimal("999999"),
            ),
            _store(),
        )
        check_feasibility(params)  # should not raise


class TestResolveEdgeCases:
    def test_taxes_not_financeable_taxes_dominate(self):
        """When purchase_taxes > total_acquisition_cost * ratio, taxes set the floor."""
        params = resolve(
            _base_inputs(
                country="FR",
                property_price=Decimal("500000"),
                purchase_taxes=Decimal("100000"),  # 20% — exceeds any ratio*total
                available_savings=Decimal("150000"),
            ),
            _store(),
        )
        # min_dp = max(100000, 600000 * 0) = 100000
        assert params.min_down_payment == Decimal("100000")

    def test_fixed_loan_duration_stored_in_sources(self):
        params = resolve(
            _base_inputs(fixed_loan_duration_months=180),
            _store(),
        )
        assert params.fixed_loan_duration_months == 180
        assert params.sources["fixed_loan_duration_months"] == "user"

    def test_default_fixed_loan_duration_is_240(self):
        from credit_simulator.config import DEFAULT_LOAN_DURATION_MONTHS
        params = resolve(_base_inputs(), _store())
        assert params.fixed_loan_duration_months == DEFAULT_LOAN_DURATION_MONTHS
        assert params.sources["fixed_loan_duration_months"] == "default"

    def test_rate_for_ltv_uses_resolved_rate(self):
        """rate_for_ltv on ResolvedParams must apply tier delta on top of resolved rate."""
        params = resolve(
            _base_inputs(annual_interest_rate=Decimal("0.04")),
            _store(),
        )
        # BE ≤75% tier has delta -0.30% → effective = 4% - 0.30% = 3.70%
        rate = params.rate_for_ltv(Decimal("0.70"))
        assert rate == Decimal("0.04") + Decimal("-0.0030")


class TestOpportunityCostRateResolution:
    def test_default_opp_rate_from_config(self):
        from credit_simulator.config import SWEET_SPOT_OPPORTUNITY_COST_RATE
        params = resolve(_base_inputs(), _store())
        assert params.opportunity_cost_rate == SWEET_SPOT_OPPORTUNITY_COST_RATE

    def test_user_supplied_opp_rate_used(self):
        params = resolve(
            _base_inputs(opportunity_cost_rate=Decimal("0.06")),
            _store(),
        )
        assert params.opportunity_cost_rate == Decimal("0.06")

    def test_zero_opp_rate_accepted(self):
        params = resolve(
            _base_inputs(opportunity_cost_rate=Decimal("0")),
            _store(),
        )
        assert params.opportunity_cost_rate == Decimal("0")

    def test_opp_rate_none_falls_back_to_default(self):
        from credit_simulator.config import SWEET_SPOT_OPPORTUNITY_COST_RATE
        params = resolve(_base_inputs(opportunity_cost_rate=None), _store())
        assert params.opportunity_cost_rate == SWEET_SPOT_OPPORTUNITY_COST_RATE
