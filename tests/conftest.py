"""Shared fixtures for the whole test suite.

Locale isolation
----------------
`cli.py` calls ``set_locale(detect_locale())`` on every invocation, and
``CliRunner`` runs the CLI in-process, so a CLI test leaves i18n's module-global
locale set to whatever the host machine reports. ``detect_locale`` falls back to
the system locale, so on a non-English workstation (e.g. ``fr_FR``) every test
that ran after ``tests/integration/test_cli.py`` and asserted on an English
message failed — while the same suite passed on an English CI runner.

Pinning both the environment override and the module global makes the suite
deterministic regardless of host locale and test execution order. Tests that
need another locale still set it explicitly (via ``set_locale`` or ``CliRunner``
``env=``), and the fixture restores the previous value afterwards.
"""
import pytest

from credit_simulator import i18n


@pytest.fixture(autouse=True)
def pin_locale(monkeypatch):
    monkeypatch.setenv("CREDIT_SIMULATOR_LOCALE", "en")
    previous = i18n.get_locale()
    i18n.set_locale("en")
    yield
    i18n.set_locale(previous)
