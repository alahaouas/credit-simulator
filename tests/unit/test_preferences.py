"""Unit tests for preferences.py — load, save, apply, and restore."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from credit_simulator import preferences as prefs
from credit_simulator.profiles import SessionProfileStore
from credit_simulator.resolver import UserInputs


def _inputs(**kwargs) -> UserInputs:
    defaults = dict(
        property_price=Decimal("300000"),
        monthly_net_income=Decimal("4000"),
        available_savings=Decimal("80000"),
    )
    defaults.update(kwargs)
    return UserInputs(**defaults)


def _prefs_file(tmp_path: Path, data: dict) -> Path:
    f = tmp_path / "preferences.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# load()
# ---------------------------------------------------------------------------

class TestLoad:
    def test_returns_empty_when_file_missing(self, tmp_path):
        with patch.object(prefs, "_PREFS_FILE", tmp_path / "missing.json"):
            assert prefs.load() == {}

    def test_returns_data_for_valid_file(self, tmp_path):
        data = {"version": 1, "inputs": {"country": "BE"}, "profile_overrides": {}, "manual_rates": []}
        f = _prefs_file(tmp_path, data)
        with patch.object(prefs, "_PREFS_FILE", f):
            assert prefs.load() == data

    def test_returns_empty_for_wrong_version(self, tmp_path):
        f = _prefs_file(tmp_path, {"version": 99, "inputs": {}})
        with patch.object(prefs, "_PREFS_FILE", f):
            assert prefs.load() == {}

    def test_returns_empty_for_non_dict(self, tmp_path):
        f = tmp_path / "preferences.json"
        f.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        with patch.object(prefs, "_PREFS_FILE", f):
            assert prefs.load() == {}

    def test_returns_empty_for_corrupt_json(self, tmp_path):
        f = tmp_path / "preferences.json"
        f.write_text("not { valid json", encoding="utf-8")
        with patch.object(prefs, "_PREFS_FILE", f):
            assert prefs.load() == {}


# ---------------------------------------------------------------------------
# save()
# ---------------------------------------------------------------------------

class TestSave:
    def test_round_trip_basic_inputs(self, tmp_path):
        inputs = _inputs(country="BE", optimization_preference="balanced")
        store = SessionProfileStore()
        prefs_file = tmp_path / "prefs.json"
        with patch.object(prefs, "_PREFS_FILE", prefs_file), \
             patch.object(prefs, "_PREFS_DIR", tmp_path):
            prefs.save(inputs, store)
            data = prefs.load()
        assert data["inputs"]["country"] == "BE"
        assert data["inputs"]["optimization_preference"] == "balanced"
        assert data["version"] == 1

    def test_decimal_fields_saved_as_strings(self, tmp_path):
        inputs = _inputs(monthly_net_income=Decimal("5000"), available_savings=Decimal("90000"))
        store = SessionProfileStore()
        prefs_file = tmp_path / "prefs.json"
        with patch.object(prefs, "_PREFS_FILE", prefs_file), \
             patch.object(prefs, "_PREFS_DIR", tmp_path):
            prefs.save(inputs, store)
            data = prefs.load()
        assert data["inputs"]["monthly_net_income"] == "5000"
        assert data["inputs"]["available_savings"] == "90000"

    def test_store_overrides_serialized(self, tmp_path):
        inputs = _inputs()
        store = SessionProfileStore()
        store.set_annual_rate("BE", "average", Decimal("0.04"), manual=True)
        prefs_file = tmp_path / "prefs.json"
        with patch.object(prefs, "_PREFS_FILE", prefs_file), \
             patch.object(prefs, "_PREFS_DIR", tmp_path):
            prefs.save(inputs, store)
            data = prefs.load()
        assert "BE" in data["profile_overrides"]


# ---------------------------------------------------------------------------
# apply_to_inputs()
# ---------------------------------------------------------------------------

class TestApplyToInputs:
    def test_restores_country(self):
        saved = {"version": 1, "inputs": {"country": "FR"}, "profile_overrides": {}, "manual_rates": []}
        inputs = _inputs()
        prefs.apply_to_inputs(saved, inputs)
        assert inputs.country == "FR"

    def test_restores_decimal_field(self):
        saved = {"version": 1, "inputs": {"monthly_net_income": "5500"}, "profile_overrides": {}, "manual_rates": []}
        inputs = _inputs()
        prefs.apply_to_inputs(saved, inputs)
        assert inputs.monthly_net_income == Decimal("5500")

    def test_restores_int_field(self):
        saved = {"version": 1, "inputs": {"max_loan_duration_months": 240}, "profile_overrides": {}, "manual_rates": []}
        inputs = _inputs()
        prefs.apply_to_inputs(saved, inputs)
        assert inputs.max_loan_duration_months == 240

    def test_skips_none_values(self):
        saved = {"version": 1, "inputs": {"country": None}, "profile_overrides": {}, "manual_rates": []}
        inputs = _inputs()
        prefs.apply_to_inputs(saved, inputs)
        assert inputs.country is None

    def test_ignores_invalid_decimal(self):
        saved = {"version": 1, "inputs": {"monthly_net_income": "not-a-number"}, "profile_overrides": {}, "manual_rates": []}
        inputs = _inputs()
        original = inputs.monthly_net_income
        prefs.apply_to_inputs(saved, inputs)
        assert inputs.monthly_net_income == original

    def test_ignores_invalid_int(self):
        saved = {"version": 1, "inputs": {"max_loan_duration_months": "bad"}, "profile_overrides": {}, "manual_rates": []}
        inputs = _inputs()
        prefs.apply_to_inputs(saved, inputs)
        assert inputs.max_loan_duration_months is None

    def test_empty_prefs_leaves_inputs_unchanged(self):
        inputs = _inputs(country="GB")
        prefs.apply_to_inputs({}, inputs)
        assert inputs.country == "GB"


# ---------------------------------------------------------------------------
# saved_decimal()
# ---------------------------------------------------------------------------

class TestSavedDecimal:
    def test_returns_decimal_for_valid_field(self):
        saved = {"version": 1, "inputs": {"opportunity_cost_rate": "0.035"}, "profile_overrides": {}, "manual_rates": []}
        result = prefs.saved_decimal(saved, "opportunity_cost_rate")
        assert result == Decimal("0.035")

    def test_returns_none_for_missing_field(self):
        assert prefs.saved_decimal({}, "opportunity_cost_rate") is None

    def test_returns_none_for_none_value(self):
        saved = {"inputs": {"opportunity_cost_rate": None}}
        assert prefs.saved_decimal(saved, "opportunity_cost_rate") is None

    def test_returns_none_for_invalid_decimal(self):
        saved = {"inputs": {"opportunity_cost_rate": "not-a-decimal"}}
        assert prefs.saved_decimal(saved, "opportunity_cost_rate") is None


# ---------------------------------------------------------------------------
# apply_to_store()
# ---------------------------------------------------------------------------

class TestApplyToStore:
    def test_restores_annual_rate(self):
        saved = {
            "profile_overrides": {"BE": {"annual_rate_average": "0.04"}},
            "manual_rates": [],
        }
        store = SessionProfileStore()
        prefs.apply_to_store(saved, store)
        assert store.get_annual_rate("BE", "average") == Decimal("0.04")

    def test_restores_insurance_rate(self):
        saved = {
            "profile_overrides": {"BE": {"insurance_rate_average": "0.003"}},
            "manual_rates": [],
        }
        store = SessionProfileStore()
        prefs.apply_to_store(saved, store)
        assert store.get_insurance_rate("BE", "average") == Decimal("0.003")

    def test_restores_string_field(self):
        saved = {
            "profile_overrides": {"BE": {"currency": "EUR"}},
            "manual_rates": [],
        }
        store = SessionProfileStore()
        prefs.apply_to_store(saved, store)
        assert store.get_field("BE", "currency") == "EUR"

    def test_restores_numeric_field(self):
        saved = {
            "profile_overrides": {"BE": {"min_down_payment_ratio": "0.25"}},
            "manual_rates": [],
        }
        store = SessionProfileStore()
        prefs.apply_to_store(saved, store)
        assert store.get_field("BE", "min_down_payment_ratio") == Decimal("0.25")

    def test_restores_manual_rate_flags(self):
        saved = {
            "profile_overrides": {},
            "manual_rates": [["BE", "average"]],
        }
        store = SessionProfileStore()
        prefs.apply_to_store(saved, store)
        assert ("BE", "average") in store._manual_rate_set

    def test_empty_prefs_leaves_store_unchanged(self):
        store = SessionProfileStore()
        original_rate = store.get_annual_rate("BE", "average")
        prefs.apply_to_store({}, store)
        assert store.get_annual_rate("BE", "average") == original_rate

    def test_ignores_invalid_rate_value(self):
        saved = {
            "profile_overrides": {"BE": {"annual_rate_average": "not-a-number"}},
            "manual_rates": [],
        }
        store = SessionProfileStore()
        original = store.get_annual_rate("BE", "average")
        prefs.apply_to_store(saved, store)
        assert store.get_annual_rate("BE", "average") == original
