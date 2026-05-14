"""`credit-simulator rates ...` subcommand group — persistent rate overrides.

These commands let users refresh country rates without reinstalling/rebuilding
the package.  Overrides are persisted to the same `~/.credit_simulator/preferences.json`
file used by the interactive simulator, so subsequent simulator runs pick them
up automatically via `preferences.apply_to_store`.

Surface:
    credit-simulator rates set    <COUNTRY> <FIELD> <VALUE>
    credit-simulator rates show   [COUNTRY]
    credit-simulator rates clear  <COUNTRY> [FIELD]
    credit-simulator rates list
    credit-simulator rates path

Refreshable FIELDs:
    annual_rate_average, annual_rate_best
    insurance_rate_average, insurance_rate_best
"""
from __future__ import annotations

import sys
from decimal import Decimal, InvalidOperation

import click
from rich import box
from rich.console import Console
from rich.table import Table

from . import preferences
from .profiles import SUPPORTED_COUNTRIES, SessionProfileStore, get_profile

_console = Console()
_err = Console(stderr=True, style="bold red")

REFRESHABLE_FIELDS: tuple[str, ...] = (
    "annual_rate_average",
    "annual_rate_best",
    "insurance_rate_average",
    "insurance_rate_best",
)


def _parse_decimal(raw: str) -> Decimal:
    try:
        return Decimal(raw.replace(",", ".").replace(" ", ""))
    except InvalidOperation as exc:
        raise click.BadParameter(f"'{raw}' is not a valid decimal.") from exc


def _validate_country(code: str) -> str:
    upper = code.upper()
    if upper not in SUPPORTED_COUNTRIES:
        supported = ", ".join(sorted(SUPPORTED_COUNTRIES))
        raise click.BadParameter(
            f"Unsupported country '{upper}'. Supported: {supported}"
        )
    return upper


def _validate_field(field: str) -> str:
    if field not in REFRESHABLE_FIELDS:
        allowed = ", ".join(REFRESHABLE_FIELDS)
        raise click.BadParameter(
            f"Field '{field}' is not refreshable. Allowed: {allowed}"
        )
    return field


def _load_store() -> SessionProfileStore:
    """Build a SessionProfileStore seeded with any persisted overrides."""
    prefs = preferences.load()
    store = SessionProfileStore()
    preferences.apply_to_store(prefs, store)
    return store


@click.group()
def rates_group() -> None:
    """Manage persisted country rate overrides."""


@rates_group.command("set")
@click.argument("country")
@click.argument("field")
@click.argument("value")
def rates_set(country: str, field: str, value: str) -> None:
    """Set COUNTRY.FIELD to VALUE and persist.

    Example: credit-simulator rates set BE annual_rate_best 0.0320
    """
    code = _validate_country(country)
    field = _validate_field(field)
    decimal_value = _parse_decimal(value)

    store = _load_store()
    try:
        if field.startswith("annual_rate_"):
            quality = field[len("annual_rate_"):]
            store.set_annual_rate(code, quality, decimal_value, manual=True)  # type: ignore[arg-type]
        else:
            quality = field[len("insurance_rate_"):]
            store.set_insurance_rate(code, quality, decimal_value)  # type: ignore[arg-type]
    except ValueError as exc:
        _err.print(str(exc))
        sys.exit(1)

    preferences.save_overrides_only(store)
    _console.print(
        f"[green]✓[/green] {code}.{field} = "
        f"[bold]{decimal_value * Decimal('100'):.4f}%[/bold] (persisted)"
    )


@rates_group.command("show")
@click.argument("country", required=False)
def rates_show(country: str | None) -> None:
    """Show the effective rates for COUNTRY (or all countries if omitted)."""
    store = _load_store()
    codes = [_validate_country(country)] if country else sorted(SUPPORTED_COUNTRIES)

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Country")
    table.add_column("Avg rate", justify="right")
    table.add_column("Best rate", justify="right")
    table.add_column("Avg insurance", justify="right")
    table.add_column("Best insurance", justify="right")
    table.add_column("Last updated")
    table.add_column("Overridden", justify="center")

    for code in codes:
        profile = get_profile(code)
        overridden = code in store._overrides and any(
            f in store._overrides[code] for f in REFRESHABLE_FIELDS
        )
        avg = store.get_annual_rate(code, "average")
        best = store.get_annual_rate(code, "best")
        ins_avg = store.get_insurance_rate(code, "average")
        ins_best = store.get_insurance_rate(code, "best")
        table.add_row(
            code,
            f"{avg * Decimal('100'):.4f}%",
            f"{best * Decimal('100'):.4f}%",
            f"{ins_avg * Decimal('100'):.4f}%",
            f"{ins_best * Decimal('100'):.4f}%",
            profile.last_updated_date or "—",
            "yes" if overridden else "—",
        )

    _console.print(table)


@rates_group.command("clear")
@click.argument("country")
@click.argument("field", required=False)
def rates_clear(country: str, field: str | None) -> None:
    """Clear persisted overrides for COUNTRY (single FIELD or all)."""
    code = _validate_country(country)
    if field is not None:
        _validate_field(field)

    store = _load_store()
    overrides = store._overrides.get(code, {})
    if not overrides:
        _console.print(f"No overrides set for {code}.")
        return

    if field is None:
        store._overrides.pop(code, None)
        store._manual_rate_set = {
            (c, q) for (c, q) in store._manual_rate_set if c != code
        }
        _console.print(f"[green]✓[/green] Cleared all overrides for {code}.")
    else:
        overrides.pop(field, None)
        if field.startswith("annual_rate_"):
            quality = field[len("annual_rate_"):]
            store._manual_rate_set.discard((code, quality))  # type: ignore[arg-type]
        if not overrides:
            store._overrides.pop(code, None)
        _console.print(f"[green]✓[/green] Cleared {code}.{field}.")

    preferences.save_overrides_only(store)


@rates_group.command("list")
def rates_list() -> None:
    """List all persisted overrides."""
    prefs = preferences.load()
    overrides = prefs.get("profile_overrides", {})
    if not overrides:
        _console.print("No persisted rate overrides.")
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Country")
    table.add_column("Field")
    table.add_column("Value", justify="right")
    for code in sorted(overrides):
        for field, value in sorted(overrides[code].items()):
            if field in REFRESHABLE_FIELDS:
                try:
                    pct = Decimal(str(value)) * Decimal("100")
                    rendered = f"{pct:.4f}%"
                except InvalidOperation:
                    rendered = str(value)
            else:
                rendered = str(value)
            table.add_row(code, field, rendered)
    _console.print(table)


@rates_group.command("path")
def rates_path() -> None:
    """Print the path of the persisted-rates config file."""
    _console.print(str(preferences._PREFS_FILE))
