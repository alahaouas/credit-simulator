"""Persistent user preferences stored in ~/.credit_simulator/preferences.json.

Saved on every update; loaded at startup to pre-fill optional inputs.
Mandatory scenario inputs (property_price, purchase_taxes, preferred_down_payment)
are intentionally excluded — they are transaction-specific.
"""
from __future__ import annotations

import contextlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .profiles import SessionProfileStore
    from .resolver import UserInputs

_PREFS_DIR = Path.home() / ".credit_simulator"
_PREFS_FILE = _PREFS_DIR / "preferences.json"
_VERSION = 1

# UserInputs fields to persist (strings and enums stored as str)
_STR_FIELDS = ("country", "profile_quality", "optimization_preference")
# Decimal fields (stored as str, None if not set)
_DECIMAL_FIELDS = (
    "opportunity_cost_rate",
    "annual_interest_rate",
    "insurance_rate",
    "min_down_payment_ratio",
    "max_debt_ratio",
    "max_monthly_payment",
    "monthly_net_income",
    "available_savings",
)
# Int fields (stored as int, None if not set)
_INT_FIELDS = ("max_loan_duration_months", "fixed_loan_duration_months")


def load() -> dict:
    """Return saved preferences, or {} if missing or corrupt."""
    if not _PREFS_FILE.exists():
        return {}
    try:
        with _PREFS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or data.get("version") != _VERSION:
            return {}
        return data
    except Exception:
        return {}


def save(inputs: UserInputs, store: SessionProfileStore) -> None:
    """Persist inputs and profile store overrides to disk."""
    _PREFS_DIR.mkdir(parents=True, exist_ok=True)

    inp: dict[str, Any] = {}
    for field in _STR_FIELDS:
        inp[field] = getattr(inputs, field, None)
    for field in _DECIMAL_FIELDS:
        val = getattr(inputs, field, None)
        inp[field] = str(val) if val is not None else None
    for field in _INT_FIELDS:
        val = getattr(inputs, field, None)
        inp[field] = int(val) if val is not None else None

    profile_overrides: dict[str, dict[str, Any]] = {}
    for country, overrides in store._overrides.items():
        serialized: dict[str, Any] = {}
        for k, v in overrides.items():
            if isinstance(v, Decimal):
                serialized[k] = str(v)
            else:
                serialized[k] = v
        profile_overrides[country] = serialized

    manual_rates = [[c, q] for c, q in store._manual_rate_set]

    with _PREFS_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            {"version": _VERSION, "inputs": inp,
             "profile_overrides": profile_overrides, "manual_rates": manual_rates},
            f, indent=2,
        )


def apply_to_inputs(prefs: dict, inputs: UserInputs) -> None:
    """Restore saved optional fields into *inputs* (in-place).

    Does NOT overwrite mandatory fields already set by the caller
    (property_price, monthly_net_income, available_savings stay as-is
    unless the caller sets them to None first).
    """
    saved = prefs.get("inputs", {})
    for field in _STR_FIELDS:
        val = saved.get(field)
        if val is not None:
            setattr(inputs, field, val)
    for field in _DECIMAL_FIELDS:
        val = saved.get(field)
        if val is not None:
            with contextlib.suppress(InvalidOperation):
                setattr(inputs, field, Decimal(str(val)))
    for field in _INT_FIELDS:
        val = saved.get(field)
        if val is not None:
            with contextlib.suppress(TypeError, ValueError):
                setattr(inputs, field, int(val))


def saved_decimal(prefs: dict, field: str) -> Decimal | None:
    """Return a single saved Decimal field, or None."""
    raw = prefs.get("inputs", {}).get(field)
    if raw is None:
        return None
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        return None


def apply_to_store(prefs: dict, store: SessionProfileStore) -> None:
    """Restore profile overrides and manual-rate flags into *store*."""
    for country, overrides in prefs.get("profile_overrides", {}).items():
        for k, v in overrides.items():
            if k.startswith("annual_rate_"):
                quality = k[len("annual_rate_"):]
                with contextlib.suppress(ValueError, InvalidOperation):
                    store.set_annual_rate(country, quality, Decimal(str(v)), manual=False)  # type: ignore[arg-type]
            elif k.startswith("insurance_rate_"):
                quality = k[len("insurance_rate_"):]
                with contextlib.suppress(ValueError, InvalidOperation):
                    store.set_insurance_rate(country, quality, Decimal(str(v)))  # type: ignore[arg-type]
            else:
                if isinstance(v, str):
                    try:
                        store.set_field(country, k, Decimal(v))
                    except InvalidOperation:
                        store.set_field(country, k, v)
                else:
                    store.set_field(country, k, v)

    for pair in prefs.get("manual_rates", []):
        if len(pair) == 2:
            store._manual_rate_set.add((pair[0], pair[1]))
