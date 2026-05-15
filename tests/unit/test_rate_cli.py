"""Unit tests for the `rates` CLI subcommand group (rate_cli.py)."""
from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import patch

from click.testing import CliRunner

from credit_simulator import preferences as prefs
from credit_simulator.rate_cli import rates_group


def _patch_prefs_file(tmp_path):
    """Patch the preferences file path to a tmp location for isolation."""
    return patch.object(prefs, "_PREFS_FILE", tmp_path / "preferences.json")


def _read_prefs(tmp_path) -> dict:
    f = tmp_path / "preferences.json"
    if not f.exists():
        return {}
    return json.loads(f.read_text(encoding="utf-8"))


class TestRatesSet:
    def test_set_persists_annual_rate_best(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            result = CliRunner().invoke(
                rates_group, ["set", "BE", "annual_rate_best", "0.0320"]
            )
            assert result.exit_code == 0, result.output
            data = _read_prefs(tmp_path)
            assert data["profile_overrides"]["BE"]["annual_rate_best"] == "0.0320"

    def test_set_persists_annual_rate_average(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            result = CliRunner().invoke(
                rates_group, ["set", "BE", "annual_rate_average", "0.0340"]
            )
            assert result.exit_code == 0
            data = _read_prefs(tmp_path)
            assert data["profile_overrides"]["BE"]["annual_rate_average"] == "0.0340"

    def test_set_persists_insurance_rate(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            result = CliRunner().invoke(
                rates_group, ["set", "BE", "insurance_rate_best", "0.0010"]
            )
            assert result.exit_code == 0
            data = _read_prefs(tmp_path)
            assert data["profile_overrides"]["BE"]["insurance_rate_best"] == "0.0010"

    def test_set_country_is_uppercased(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            result = CliRunner().invoke(
                rates_group, ["set", "be", "annual_rate_best", "0.0320"]
            )
            assert result.exit_code == 0
            data = _read_prefs(tmp_path)
            assert "BE" in data["profile_overrides"]

    def test_set_rejects_unsupported_country(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            result = CliRunner().invoke(
                rates_group, ["set", "ZZ", "annual_rate_best", "0.0320"]
            )
            assert result.exit_code != 0
            assert "Unsupported" in result.output

    def test_set_rejects_non_refreshable_field(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            result = CliRunner().invoke(
                rates_group, ["set", "BE", "max_debt_ratio", "0.40"]
            )
            assert result.exit_code != 0
            assert "not refreshable" in result.output

    def test_set_rejects_invalid_decimal(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            result = CliRunner().invoke(
                rates_group, ["set", "BE", "annual_rate_best", "not-a-number"]
            )
            assert result.exit_code != 0

    def test_set_rejects_best_exceeding_average(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            # BE static average is 0.0340 — setting best to 0.99 must fail
            result = CliRunner().invoke(
                rates_group, ["set", "BE", "annual_rate_best", "0.99"]
            )
            assert result.exit_code != 0
            assert "cannot exceed" in result.output

    def test_set_rejects_average_below_best(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            # BE static best is 0.0320 — setting average to 0.001 must fail
            result = CliRunner().invoke(
                rates_group, ["set", "BE", "annual_rate_average", "0.001"]
            )
            assert result.exit_code != 0
            assert "cannot be lower" in result.output

    def test_set_accepts_comma_as_decimal_separator(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            result = CliRunner().invoke(
                rates_group, ["set", "BE", "annual_rate_best", "0,031"]
            )
            assert result.exit_code == 0
            data = _read_prefs(tmp_path)
            assert data["profile_overrides"]["BE"]["annual_rate_best"] == "0.031"

    def test_set_preserves_existing_inputs_block(self, tmp_path):
        # Seed an existing file with an inputs block
        existing = {
            "version": 1,
            "inputs": {"country": "BE", "monthly_net_income": "6000"},
            "profile_overrides": {},
            "manual_rates": [],
        }
        (tmp_path / "preferences.json").write_text(json.dumps(existing), encoding="utf-8")
        with _patch_prefs_file(tmp_path):
            result = CliRunner().invoke(
                rates_group, ["set", "BE", "annual_rate_best", "0.0310"]
            )
            assert result.exit_code == 0
            data = _read_prefs(tmp_path)
            assert data["inputs"]["country"] == "BE"
            assert data["inputs"]["monthly_net_income"] == "6000"
            assert data["profile_overrides"]["BE"]["annual_rate_best"] == "0.0310"


class TestRatesShow:
    def test_show_all_countries_no_overrides(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            result = CliRunner().invoke(rates_group, ["show"])
            assert result.exit_code == 0
            assert "BE" in result.output

    def test_show_single_country(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            result = CliRunner().invoke(rates_group, ["show", "BE"])
            assert result.exit_code == 0
            assert "BE" in result.output
            # Static avg is 3.40%, formatted as "3.4000%"
            assert "3.4000%" in result.output

    def test_show_reflects_persisted_override(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            CliRunner().invoke(
                rates_group, ["set", "BE", "annual_rate_best", "0.0310"]
            )
            result = CliRunner().invoke(rates_group, ["show", "BE"])
            assert result.exit_code == 0
            assert "3.1000%" in result.output
            assert "yes" in result.output

    def test_show_rejects_unsupported_country(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            result = CliRunner().invoke(rates_group, ["show", "ZZ"])
            assert result.exit_code != 0


class TestRatesClear:
    def test_clear_removes_all_overrides_for_country(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            CliRunner().invoke(rates_group, ["set", "BE", "annual_rate_best", "0.0310"])
            result = CliRunner().invoke(rates_group, ["clear", "-y", "BE"])
            assert result.exit_code == 0
            data = _read_prefs(tmp_path)
            assert "BE" not in data["profile_overrides"]

    def test_clear_specific_field(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            CliRunner().invoke(rates_group, ["set", "BE", "annual_rate_best", "0.0310"])
            CliRunner().invoke(rates_group, ["set", "BE", "insurance_rate_best", "0.0010"])
            result = CliRunner().invoke(
                rates_group, ["clear", "-y", "BE", "annual_rate_best"]
            )
            assert result.exit_code == 0
            data = _read_prefs(tmp_path)
            assert "annual_rate_best" not in data["profile_overrides"].get("BE", {})
            assert data["profile_overrides"]["BE"]["insurance_rate_best"] == "0.0010"

    def test_clear_no_op_when_nothing_set(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            result = CliRunner().invoke(rates_group, ["clear", "BE"])
            assert result.exit_code == 0
            assert "No overrides" in result.output

    def test_clear_drops_manual_flag(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            CliRunner().invoke(rates_group, ["set", "BE", "annual_rate_best", "0.0310"])
            data = _read_prefs(tmp_path)
            assert ["BE", "best"] in data["manual_rates"]

            CliRunner().invoke(rates_group, ["clear", "-y", "BE"])
            data = _read_prefs(tmp_path)
            assert ["BE", "best"] not in data["manual_rates"]


class TestRatesList:
    def test_list_empty_state(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            result = CliRunner().invoke(rates_group, ["list"])
            assert result.exit_code == 0
            assert "No persisted" in result.output

    def test_list_shows_overrides(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            CliRunner().invoke(rates_group, ["set", "BE", "annual_rate_best", "0.0310"])
            CliRunner().invoke(rates_group, ["set", "FR", "annual_rate_best", "0.0290"])
            result = CliRunner().invoke(rates_group, ["list"])
            assert result.exit_code == 0
            assert "BE" in result.output
            assert "FR" in result.output
            assert "3.1000%" in result.output


class TestRatesPath:
    def test_path_prints_file_location(self, tmp_path):
        with _patch_prefs_file(tmp_path):
            result = CliRunner().invoke(rates_group, ["path"])
            assert result.exit_code == 0
            assert "preferences.json" in result.output


class TestRoundTrip:
    """End-to-end: set → reload as SessionProfileStore via preferences.apply_to_store."""

    def test_persisted_override_restores_via_apply_to_store(self, tmp_path):
        from credit_simulator.profiles import SessionProfileStore

        with _patch_prefs_file(tmp_path):
            CliRunner().invoke(rates_group, ["set", "BE", "annual_rate_best", "0.0310"])
            loaded = prefs.load()

            store = SessionProfileStore()
            prefs.apply_to_store(loaded, store)
            assert store.get_annual_rate("BE", "best") == Decimal("0.0310")
