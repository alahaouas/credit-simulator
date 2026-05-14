"""Unit tests for i18n.py — locale detection, set, and get."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from credit_simulator.i18n import detect_locale, get_locale, set_locale


@pytest.fixture(autouse=True)
def restore_locale():
    original = get_locale()
    yield
    set_locale(original)


class TestSetLocale:
    def test_sets_supported_locale(self):
        set_locale("fr")
        assert get_locale() == "fr"

    def test_ignores_unsupported_locale(self):
        set_locale("en")
        set_locale("zz")
        assert get_locale() == "en"

    def test_normalizes_region_suffix(self):
        set_locale("fr_BE")
        assert get_locale() == "fr"

    def test_normalizes_dash_separator(self):
        set_locale("fr-FR")
        assert get_locale() == "fr"

    def test_case_insensitive(self):
        set_locale("FR")
        assert get_locale() == "fr"


class TestDetectLocale:
    def test_credit_simulator_locale_takes_priority(self):
        env = {"CREDIT_SIMULATOR_LOCALE": "fr", "LANG": "en_US.UTF-8"}
        with patch.dict(os.environ, env):
            assert detect_locale() == "fr"

    def test_unsupported_credit_simulator_locale_falls_through(self):
        env = {"CREDIT_SIMULATOR_LOCALE": "zz", "LANG": "fr_FR.UTF-8"}
        with patch.dict(os.environ, env):
            result = detect_locale()
            assert result == "fr"

    def test_lang_env_used_when_no_app_override(self):
        env = {"LANG": "fr_FR.UTF-8"}
        with patch.dict(os.environ, env):
            env_copy = os.environ.copy()
            env_copy.pop("CREDIT_SIMULATOR_LOCALE", None)
            with patch.dict(os.environ, env_copy, clear=True):
                assert detect_locale() == "fr"

    def test_defaults_to_en_when_no_locale_detected(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("credit_simulator.i18n._sys_locale") as mock_sys,
        ):
            mock_sys.getlocale.return_value = (None, None)
            assert detect_locale() == "en"

    def test_handles_sys_locale_exception(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("credit_simulator.i18n._sys_locale") as mock_sys,
        ):
            mock_sys.getlocale.side_effect = Exception("locale error")
            assert detect_locale() == "en"
