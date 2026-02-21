"""Static country profile data.

All rate fields are stored as Decimal strings to avoid float imprecision.
Each country has two profile qualities: 'average' and 'best'.
Quality only affects market-driven fields (annual_rate, insurance_rate).
Regulatory fields are identical across both qualities.

LTV rate tiers model real-world risk-based pricing: lower down payment
(higher LTV) triggers a rate surcharge; higher down payment (lower LTV)
earns a discount.  Tiers are ordered by ascending ltv_max; the first tier
whose ltv_max >= the loan's LTV applies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .config import DEFAULT_COUNTRY, DEFAULT_QUALITY, ProfileQuality


@dataclass(frozen=True)
class LtvRateTier:
    """One LTV band and its rate adjustment (delta added to the base rate).

    rate_delta < 0  → discount (reward for lower LTV / bigger equity)
    rate_delta > 0  → surcharge (penalty for higher LTV / smaller equity)
    Tiers must be listed in ascending ltv_max order.
    """
    ltv_max: Decimal    # inclusive upper bound, e.g. Decimal("0.80") = 80% LTV
    rate_delta: Decimal # e.g. Decimal("-0.0015") = -0.15 percentage points


@dataclass(frozen=True)
class CountryProfile:
    code: str
    currency: str
    # Market-driven (quality-sensitive)
    annual_rate_average: Decimal
    annual_rate_best: Decimal
    insurance_rate_average: Decimal
    insurance_rate_best: Decimal
    # Regulatory (same for both qualities)
    purchase_tax_rate: Decimal
    taxes_financeable: bool
    min_down_payment_ratio: Decimal
    max_loan_duration_months: int
    # LTV-based rate adjustment tiers (ascending ltv_max order)
    ltv_rate_tiers: tuple = ()   # tuple[LtvRateTier, ...]

    def annual_rate(self, quality: ProfileQuality) -> Decimal:
        return self.annual_rate_average if quality == "average" else self.annual_rate_best

    def insurance_rate(self, quality: ProfileQuality) -> Decimal:
        return self.insurance_rate_average if quality == "average" else self.insurance_rate_best

    def rate_for_ltv(self, ltv: Decimal, quality: ProfileQuality) -> Decimal:
        """Effective annual rate after applying the matching LTV tier delta."""
        base = self.annual_rate(quality)
        for tier in self.ltv_rate_tiers:
            if ltv <= tier.ltv_max:
                return base + tier.rate_delta
        if self.ltv_rate_tiers:
            return base + self.ltv_rate_tiers[-1].rate_delta
        return base


# ── LTV tier helpers ──────────────────────────────────────────────────────────

def _be_tiers() -> tuple:
    return (
        LtvRateTier(Decimal("0.75"), Decimal("-0.0025")),  # LTV ≤ 75%: −0.25%
        LtvRateTier(Decimal("0.80"), Decimal("-0.0015")),  # LTV ≤ 80%: −0.15%
        LtvRateTier(Decimal("0.90"), Decimal("0.0000")),   # LTV ≤ 90%: base
        LtvRateTier(Decimal("1.00"), Decimal("0.0025")),   # LTV ≤ 100%: +0.25%
    )

def _fr_tiers() -> tuple:
    return (
        LtvRateTier(Decimal("0.75"), Decimal("-0.0020")),  # LTV ≤ 75%: −0.20%
        LtvRateTier(Decimal("0.80"), Decimal("-0.0010")),  # LTV ≤ 80%: −0.10%
        LtvRateTier(Decimal("0.90"), Decimal("0.0000")),   # LTV ≤ 90%: base
        LtvRateTier(Decimal("1.00"), Decimal("0.0030")),   # LTV ≤ 100%: +0.30%
    )

def _de_tiers() -> tuple:
    return (
        LtvRateTier(Decimal("0.60"), Decimal("-0.0025")),  # LTV ≤ 60%: −0.25%
        LtvRateTier(Decimal("0.80"), Decimal("-0.0010")),  # LTV ≤ 80%: −0.10%
        LtvRateTier(Decimal("0.90"), Decimal("0.0000")),   # LTV ≤ 90%: base
        LtvRateTier(Decimal("1.00"), Decimal("0.0030")),   # LTV ≤ 100%: +0.30%
    )

def _es_tiers() -> tuple:
    return (
        LtvRateTier(Decimal("0.75"), Decimal("-0.0020")),
        LtvRateTier(Decimal("0.80"), Decimal("-0.0010")),
        LtvRateTier(Decimal("0.90"), Decimal("0.0000")),
        LtvRateTier(Decimal("1.00"), Decimal("0.0025")),
    )

def _pt_tiers() -> tuple:
    return (
        LtvRateTier(Decimal("0.75"), Decimal("-0.0020")),
        LtvRateTier(Decimal("0.80"), Decimal("-0.0010")),
        LtvRateTier(Decimal("0.90"), Decimal("0.0000")),
        LtvRateTier(Decimal("1.00"), Decimal("0.0030")),
    )

def _it_tiers() -> tuple:
    return (
        LtvRateTier(Decimal("0.75"), Decimal("-0.0020")),
        LtvRateTier(Decimal("0.80"), Decimal("-0.0010")),
        LtvRateTier(Decimal("0.90"), Decimal("0.0000")),
        LtvRateTier(Decimal("1.00"), Decimal("0.0030")),
    )

def _gb_tiers() -> tuple:
    return (
        LtvRateTier(Decimal("0.60"), Decimal("-0.0030")),  # LTV ≤ 60%: −0.30%
        LtvRateTier(Decimal("0.75"), Decimal("-0.0015")),  # LTV ≤ 75%: −0.15%
        LtvRateTier(Decimal("0.90"), Decimal("0.0000")),   # LTV ≤ 90%: base
        LtvRateTier(Decimal("1.00"), Decimal("0.0050")),   # LTV ≤ 100%: +0.50%
    )

def _us_tiers() -> tuple:
    return (
        LtvRateTier(Decimal("0.80"), Decimal("-0.0025")),  # LTV ≤ 80%: −0.25%
        LtvRateTier(Decimal("0.90"), Decimal("0.0000")),   # LTV ≤ 90%: base
        LtvRateTier(Decimal("1.00"), Decimal("0.0075")),   # LTV ≤ 100%: +0.75%
    )


# Static embedded profiles — all rates expressed as annual fractions (e.g. 0.035 = 3.5%)
_PROFILES: dict[str, CountryProfile] = {
    "FR": CountryProfile(
        code="FR",
        currency="EUR",
        annual_rate_average=Decimal("0.0350"),
        annual_rate_best=Decimal("0.0290"),
        insurance_rate_average=Decimal("0.0030"),
        insurance_rate_best=Decimal("0.0010"),
        purchase_tax_rate=Decimal("0.075"),
        taxes_financeable=False,
        min_down_payment_ratio=Decimal("0.00"),  # minimum = taxes (handled in resolver)
        max_loan_duration_months=300,
        ltv_rate_tiers=_fr_tiers(),
    ),
    "ES": CountryProfile(
        code="ES",
        currency="EUR",
        annual_rate_average=Decimal("0.0350"),
        annual_rate_best=Decimal("0.0280"),
        insurance_rate_average=Decimal("0.0020"),
        insurance_rate_best=Decimal("0.0009"),
        purchase_tax_rate=Decimal("0.08"),
        taxes_financeable=True,
        min_down_payment_ratio=Decimal("0.20"),
        max_loan_duration_months=360,
        ltv_rate_tiers=_es_tiers(),
    ),
    "DE": CountryProfile(
        code="DE",
        currency="EUR",
        annual_rate_average=Decimal("0.0380"),
        annual_rate_best=Decimal("0.0310"),
        insurance_rate_average=Decimal("0.0015"),
        insurance_rate_best=Decimal("0.0008"),
        purchase_tax_rate=Decimal("0.05"),
        taxes_financeable=True,
        min_down_payment_ratio=Decimal("0.20"),
        max_loan_duration_months=360,
        ltv_rate_tiers=_de_tiers(),
    ),
    "PT": CountryProfile(
        code="PT",
        currency="EUR",
        annual_rate_average=Decimal("0.0400"),
        annual_rate_best=Decimal("0.0320"),
        insurance_rate_average=Decimal("0.0025"),
        insurance_rate_best=Decimal("0.0010"),
        purchase_tax_rate=Decimal("0.07"),
        taxes_financeable=True,
        min_down_payment_ratio=Decimal("0.10"),
        max_loan_duration_months=360,
        ltv_rate_tiers=_pt_tiers(),
    ),
    "BE": CountryProfile(
        code="BE",
        currency="EUR",
        annual_rate_average=Decimal("0.0320"),
        annual_rate_best=Decimal("0.0270"),
        insurance_rate_average=Decimal("0.0025"),
        insurance_rate_best=Decimal("0.0010"),
        purchase_tax_rate=Decimal("0.125"),
        taxes_financeable=True,
        min_down_payment_ratio=Decimal("0.20"),
        max_loan_duration_months=300,
        ltv_rate_tiers=_be_tiers(),
    ),
    "IT": CountryProfile(
        code="IT",
        currency="EUR",
        annual_rate_average=Decimal("0.0400"),
        annual_rate_best=Decimal("0.0320"),
        insurance_rate_average=Decimal("0.0020"),
        insurance_rate_best=Decimal("0.0008"),
        purchase_tax_rate=Decimal("0.04"),
        taxes_financeable=True,
        min_down_payment_ratio=Decimal("0.20"),
        max_loan_duration_months=360,
        ltv_rate_tiers=_it_tiers(),
    ),
    "GB": CountryProfile(
        code="GB",
        currency="GBP",
        annual_rate_average=Decimal("0.0500"),
        annual_rate_best=Decimal("0.0420"),
        insurance_rate_average=Decimal("0.0025"),
        insurance_rate_best=Decimal("0.0012"),
        purchase_tax_rate=Decimal("0.03"),
        taxes_financeable=True,
        min_down_payment_ratio=Decimal("0.10"),
        max_loan_duration_months=420,
        ltv_rate_tiers=_gb_tiers(),
    ),
    "US": CountryProfile(
        code="US",
        currency="USD",
        annual_rate_average=Decimal("0.0700"),
        annual_rate_best=Decimal("0.0620"),
        insurance_rate_average=Decimal("0.0080"),
        insurance_rate_best=Decimal("0.0040"),
        purchase_tax_rate=Decimal("0.025"),
        taxes_financeable=True,
        min_down_payment_ratio=Decimal("0.20"),
        max_loan_duration_months=360,
        ltv_rate_tiers=_us_tiers(),
    ),
}

SUPPORTED_COUNTRIES = frozenset(_PROFILES.keys())


def get_profile(country: str) -> CountryProfile:
    """Return the static profile for *country* (upper-cased).

    Raises ValueError for unknown country codes.
    """
    code = country.upper()
    if code not in _PROFILES:
        raise ValueError(
            f"Unsupported country code '{code}'. "
            f"Supported codes: {', '.join(sorted(SUPPORTED_COUNTRIES))}"
        )
    return _PROFILES[code]


class SessionProfileStore:
    """Mutable, session-scoped overlay on top of the static profiles.

    Modifications are stored in a per-country dict keyed by field name.
    The static profile is read-through for any field not overridden.
    """

    def __init__(self) -> None:
        # Overrides stored as {country_code: {field: value}}
        self._overrides: dict[str, dict[str, object]] = {}
        # Track which annual_rate values were manually set by the user
        # (to decide whether online fetch should prompt for confirmation)
        self._manual_rate_set: set[tuple[str, ProfileQuality]] = set()

    def get_rate_for_ltv(self, country: str, quality: ProfileQuality, ltv: Decimal) -> Decimal:
        """Base rate (with any session override applied) plus the LTV tier delta."""
        base = self.get_annual_rate(country, quality)
        profile = get_profile(country.upper())
        for tier in profile.ltv_rate_tiers:
            if ltv <= tier.ltv_max:
                return base + tier.rate_delta
        if profile.ltv_rate_tiers:
            return base + profile.ltv_rate_tiers[-1].rate_delta
        return base

    def get_annual_rate(self, country: str, quality: ProfileQuality) -> Decimal:
        code = country.upper()
        key = f"annual_rate_{quality}"
        overrides = self._overrides.get(code, {})
        if key in overrides:
            return overrides[key]  # type: ignore[return-value]
        return get_profile(code).annual_rate(quality)

    def get_insurance_rate(self, country: str, quality: ProfileQuality) -> Decimal:
        code = country.upper()
        key = f"insurance_rate_{quality}"
        overrides = self._overrides.get(code, {})
        if key in overrides:
            return overrides[key]  # type: ignore[return-value]
        return get_profile(code).insurance_rate(quality)

    def get_field(self, country: str, field: str) -> object:
        """Get a non-quality-sensitive field, respecting any session override."""
        code = country.upper()
        overrides = self._overrides.get(code, {})
        if field in overrides:
            return overrides[field]
        return getattr(get_profile(code), field)

    def set_annual_rate(
        self, country: str, quality: ProfileQuality, value: Decimal, *, manual: bool
    ) -> None:
        code = country.upper()
        self._validate_rate_invariant(code, quality, value)
        self._overrides.setdefault(code, {})[f"annual_rate_{quality}"] = value
        if manual:
            self._manual_rate_set.add((code, quality))

    def set_insurance_rate(
        self, country: str, quality: ProfileQuality, value: Decimal
    ) -> None:
        code = country.upper()
        self._validate_insurance_invariant(code, quality, value)
        self._overrides.setdefault(code, {})[f"insurance_rate_{quality}"] = value

    def set_field(self, country: str, field: str, value: object) -> None:
        code = country.upper()
        self._overrides.setdefault(code, {})[field] = value

    def is_annual_rate_manually_set(self, country: str, quality: ProfileQuality) -> bool:
        return (country.upper(), quality) in self._manual_rate_set

    def _validate_rate_invariant(
        self, code: str, quality: ProfileQuality, value: Decimal
    ) -> None:
        """Ensure best <= average after the proposed update."""
        if quality == "best":
            avg = self.get_annual_rate(code, "average")
            if value > avg:
                raise ValueError(
                    f"'best' annual rate ({value:%}) cannot exceed "
                    f"'average' rate ({avg:%}) for {code}."
                )
        else:  # quality == "average"
            best = self.get_annual_rate(code, "best")
            if value < best:
                raise ValueError(
                    f"'average' annual rate ({value:%}) cannot be lower than "
                    f"'best' rate ({best:%}) for {code}."
                )

    def _validate_insurance_invariant(
        self, code: str, quality: ProfileQuality, value: Decimal
    ) -> None:
        if quality == "best":
            avg = self.get_insurance_rate(code, "average")
            if value > avg:
                raise ValueError(
                    f"'best' insurance rate ({value:%}) cannot exceed "
                    f"'average' rate ({avg:%}) for {code}."
                )
        else:
            best = self.get_insurance_rate(code, "best")
            if value < best:
                raise ValueError(
                    f"'average' insurance rate ({value:%}) cannot be lower than "
                    f"'best' rate ({best:%}) for {code}."
                )
