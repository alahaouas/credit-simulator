"""Unit tests for profiles.py — static profiles, LTV tier lookup, SessionProfileStore."""
from decimal import Decimal

import pytest

from credit_simulator.profiles import (
    CountryProfile,
    LtvRateTier,
    SessionProfileStore,
    get_profile,
)

ZERO = Decimal("0")


class TestGetProfile:
    def test_returns_known_country(self):
        profile = get_profile("BE")
        assert profile.code == "BE"
        assert profile.currency == "EUR"

    def test_case_insensitive(self):
        assert get_profile("be") == get_profile("BE")

    def test_unknown_country_raises(self):
        with pytest.raises(ValueError, match="Unsupported country code"):
            get_profile("ZZ")

    def test_all_supported_countries(self):
        for code in ("BE", "FR", "DE", "ES", "IT", "PT", "GB", "US"):
            profile = get_profile(code)
            assert profile.code == code


class TestCountryProfileRates:
    def test_average_rate_for_be(self):
        profile = get_profile("BE")
        assert profile.annual_rate("average") == Decimal("0.0327")

    def test_best_rate_for_be(self):
        profile = get_profile("BE")
        assert profile.annual_rate("best") == Decimal("0.0305")

    def test_best_rate_le_average_for_all_countries(self):
        """Invariant: best rate must be <= average for every country."""
        for code in ("BE", "FR", "DE", "ES", "IT", "PT", "GB", "US"):
            p = get_profile(code)
            assert p.annual_rate_best <= p.annual_rate_average, (
                f"{code}: best rate {p.annual_rate_best} > average {p.annual_rate_average}"
            )

    def test_best_insurance_le_average_for_all_countries(self):
        for code in ("BE", "FR", "DE", "ES", "IT", "PT", "GB", "US"):
            p = get_profile(code)
            assert p.insurance_rate_best <= p.insurance_rate_average, (
                f"{code}: best insurance {p.insurance_rate_best} > average {p.insurance_rate_average}"
            )


class TestLtvRateTierLookup:
    """Tests for CountryProfile.rate_for_ltv() — LTV tier matching."""

    def _be(self) -> CountryProfile:
        return get_profile("BE")

    def test_ltv_in_first_tier(self):
        """LTV=70% falls in BE's ≤75% tier: rate_delta = -0.30%."""
        profile = self._be()
        rate = profile.rate_for_ltv(Decimal("0.70"), "average")
        expected = Decimal("0.0327") + Decimal("-0.0030")
        assert rate == expected

    def test_ltv_at_tier_boundary(self):
        """LTV exactly at boundary belongs to that tier (inclusive upper bound)."""
        profile = self._be()
        rate = profile.rate_for_ltv(Decimal("0.75"), "average")
        expected = Decimal("0.0327") + Decimal("-0.0030")
        assert rate == expected

    def test_ltv_just_above_boundary(self):
        """LTV=0.751 falls in the ≤80% tier."""
        profile = self._be()
        rate = profile.rate_for_ltv(Decimal("0.751"), "average")
        expected = Decimal("0.0327") + Decimal("-0.0020")
        assert rate == expected

    def test_ltv_base_tier(self):
        """LTV=85% falls in BE's ≤90% tier: rate_delta = 0.00%."""
        profile = self._be()
        rate = profile.rate_for_ltv(Decimal("0.85"), "average")
        assert rate == Decimal("0.0327")

    def test_ltv_surcharge_tier(self):
        """LTV=95% falls in BE's ≤100% tier: rate_delta = +0.35%."""
        profile = self._be()
        rate = profile.rate_for_ltv(Decimal("0.95"), "average")
        expected = Decimal("0.0327") + Decimal("0.0035")
        assert rate == expected

    def test_no_tiers_returns_base_rate(self):
        """If a profile has no tiers, rate_for_ltv returns the base rate unchanged."""
        profile = CountryProfile(
            code="XX",
            currency="EUR",
            annual_rate_average=Decimal("0.04"),
            annual_rate_best=Decimal("0.03"),
            insurance_rate_average=Decimal("0.002"),
            insurance_rate_best=Decimal("0.001"),
            purchase_tax_rate=Decimal("0.05"),
            taxes_financeable=True,
            min_down_payment_ratio=Decimal("0.20"),
            max_debt_ratio=Decimal("0.35"),
            max_loan_duration_months=240,
            ltv_rate_tiers=(),
        )
        assert profile.rate_for_ltv(Decimal("0.90"), "average") == Decimal("0.04")

    def test_ltv_beyond_max_tier_uses_last_delta(self):
        """LTV above all tiers falls back to the last tier's delta."""
        # BE last tier covers ≤100%; use LTV = 100% exactly
        profile = self._be()
        rate = profile.rate_for_ltv(Decimal("1.00"), "average")
        expected = Decimal("0.0327") + Decimal("0.0035")
        assert rate == expected


class TestSessionProfileStore:
    def _store(self) -> SessionProfileStore:
        return SessionProfileStore()

    def test_get_annual_rate_returns_static_default(self):
        store = self._store()
        assert store.get_annual_rate("BE", "average") == Decimal("0.0327")

    def test_set_and_get_annual_rate(self):
        store = self._store()
        store.set_annual_rate("BE", "average", Decimal("0.04"), manual=True)
        assert store.get_annual_rate("BE", "average") == Decimal("0.04")

    def test_set_annual_rate_best_cannot_exceed_average(self):
        store = self._store()
        with pytest.raises(ValueError, match="cannot exceed"):
            store.set_annual_rate("BE", "best", Decimal("0.99"), manual=True)

    def test_set_annual_rate_average_cannot_be_below_best(self):
        store = self._store()
        with pytest.raises(ValueError, match="cannot be lower"):
            store.set_annual_rate("BE", "average", Decimal("0.001"), manual=True)

    def test_manual_flag_tracked(self):
        store = self._store()
        assert not store.is_annual_rate_manually_set("BE", "average")
        store.set_annual_rate("BE", "average", Decimal("0.04"), manual=True)
        assert store.is_annual_rate_manually_set("BE", "average")

    def test_online_update_not_flagged_as_manual(self):
        store = self._store()
        store.set_annual_rate("BE", "average", Decimal("0.033"), manual=False)
        assert not store.is_annual_rate_manually_set("BE", "average")

    def test_get_insurance_rate_returns_static_default(self):
        store = self._store()
        assert store.get_insurance_rate("BE", "average") == Decimal("0.0020")

    def test_set_insurance_rate_best_cannot_exceed_average(self):
        store = self._store()
        with pytest.raises(ValueError, match="cannot exceed"):
            store.set_insurance_rate("BE", "best", Decimal("0.99"))

    def test_set_field_overrides_regulatory_param(self):
        store = self._store()
        store.set_field("BE", "max_debt_ratio", Decimal("0.28"))
        assert store.get_field("BE", "max_debt_ratio") == Decimal("0.28")

    def test_get_field_falls_through_to_static(self):
        store = self._store()
        assert store.get_field("BE", "purchase_tax_rate") == Decimal("0.125")

    def test_get_rate_for_ltv_applies_tier_delta(self):
        """SessionProfileStore.get_rate_for_ltv applies the correct tier."""
        store = self._store()
        # LTV 70% → ≤75% tier, delta = -0.30%
        rate = store.get_rate_for_ltv("BE", "average", Decimal("0.70"))
        assert rate == Decimal("0.0327") + Decimal("-0.0030")

    def test_be_last_updated_date(self):
        """BE profile has a non-empty last_updated_date."""
        profile = get_profile("BE")
        assert profile.last_updated_date != ""

    def test_validation_error_message_is_valid_string(self):
        """Rate validation error messages must not raise TypeError (Decimal % format bug)."""
        store = self._store()
        with pytest.raises(ValueError) as exc_info:
            store.set_annual_rate("BE", "best", Decimal("0.99"), manual=True)
        msg = str(exc_info.value)
        assert "%" in msg
        assert "BE" in msg

    def test_insurance_validation_error_message_is_valid_string(self):
        store = self._store()
        with pytest.raises(ValueError) as exc_info:
            store.set_insurance_rate("BE", "best", Decimal("0.99"))
        msg = str(exc_info.value)
        assert "%" in msg
        assert "BE" in msg


class TestLtvTierInvariants:
    """Structural invariants that all country LTV tier definitions must satisfy."""

    ALL_COUNTRIES = ("BE", "FR", "DE", "ES", "IT", "PT", "GB", "US")

    @pytest.mark.parametrize("code", ALL_COUNTRIES)
    def test_ltv_tiers_ascending_ltv_max(self, code):
        """LTV tier list must be ordered by ascending ltv_max."""
        profile = get_profile(code)
        tiers = profile.ltv_rate_tiers
        for i in range(len(tiers) - 1):
            assert tiers[i].ltv_max < tiers[i + 1].ltv_max, (
                f"{code}: tier {i} ltv_max={tiers[i].ltv_max} >= "
                f"tier {i+1} ltv_max={tiers[i+1].ltv_max}"
            )

    @pytest.mark.parametrize("code", ALL_COUNTRIES)
    def test_ltv_tier_max_values_positive(self, code):
        """Every LTV cap must be a positive fraction (0 < ltv_max <= 1.5)."""
        profile = get_profile(code)
        for tier in profile.ltv_rate_tiers:
            assert ZERO < tier.ltv_max <= Decimal("1.5"), (
                f"{code}: ltv_max={tier.ltv_max} out of range"
            )

    @pytest.mark.parametrize("code", ALL_COUNTRIES)
    def test_effective_rate_always_positive(self, code):
        """rate_delta must not make the effective rate negative for any LTV."""
        profile = get_profile(code)
        base = profile.annual_rate("average")
        for tier in profile.ltv_rate_tiers:
            effective = base + tier.rate_delta
            assert effective > ZERO, (
                f"{code}: effective rate {effective} <= 0 at ltv_max={tier.ltv_max}"
            )
