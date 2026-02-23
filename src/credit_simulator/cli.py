"""Interactive CLI — click entry point + interactive update loop (§5).

Session startup:
  1. Prompt for mandatory fields (property_price, monthly_net_income, available_savings).
  2. Run simulation with auto-resolved defaults.
  3. Enter the interactive update loop.

Update loop:
  - Display current parameters and results.
  - Let the user update any field, change preference, reset to profile default,
    update a country profile field (manual or online), or exit.
"""
from __future__ import annotations

import sys
from decimal import Decimal, InvalidOperation
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from .calculator import build_amortization_schedule
from .fetcher import FetchError, fetch_rate
from .config import DEFAULT_COUNTRY, DEFAULT_QUALITY, DEFAULT_LOAN_DURATION_MONTHS, VALID_PREFERENCES
from .optimizer import OptimizedResult, SweetSpotAnalysis, optimize, analyze_sweet_spot
from .profiles import (
    SUPPORTED_COUNTRIES,
    SessionProfileStore,
    get_profile,
)
from .resolver import InfeasibleError, ResolvedParams, UserInputs, check_feasibility, resolve

console = Console()
err_console = Console(stderr=True, style="bold red")

# ──────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ──────────────────────────────────────────────────────────────────────────────

def _fmt_money(value: Decimal, currency: str) -> str:
    return f"{value:,.2f} {currency}"


def _fmt_pct(value: Decimal) -> str:
    return f"{float(value) * 100:.4f}%"


def _fmt_months(n: int) -> str:
    years, months = divmod(n, 12)
    if months == 0:
        return f"{n} months ({years} years)"
    return f"{n} months ({years}y {months}m)"


# ──────────────────────────────────────────────────────────────────────────────
# Result display
# ──────────────────────────────────────────────────────────────────────────────

def display_result(result: OptimizedResult) -> None:
    cur = result.currency

    console.print()
    console.print(Panel(
        f"[bold green]Optimal Loan Plan[/bold green] — "
        f"{result.country} / {result.profile_quality} / preference: {result.optimization_preference}",
        expand=False,
    ))

    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    t.add_column("Field", style="cyan")
    t.add_column("Value", justify="right")

    plan = result.plan
    t.add_row("Down payment", _fmt_money(result.down_payment, cur))
    t.add_row("Loan principal", _fmt_money(result.loan_principal, cur))
    t.add_row("Loan duration", _fmt_months(result.loan_duration_months))
    t.add_row("Monthly installment", _fmt_money(plan.monthly_installment, cur))
    t.add_row("  └ EMI (P+I)", _fmt_money(plan.monthly_emi, cur))
    t.add_row("  └ Insurance", _fmt_money(plan.monthly_insurance, cur))
    t.add_row("First month interest", _fmt_money(plan.monthly_interest_first, cur))
    t.add_row("APR (effective annual rate)", _fmt_pct(plan.effective_annual_rate))
    t.add_row("Total interest paid", _fmt_money(plan.total_interest_paid, cur))
    t.add_row("Total insurance paid", _fmt_money(plan.total_insurance_paid, cur))
    t.add_row("Total cost of credit", _fmt_money(plan.total_cost_of_credit, cur))
    t.add_row("Total repaid", _fmt_money(plan.total_repaid, cur))
    debt_ratio = plan.monthly_installment / result.monthly_net_income
    t.add_row("Debt ratio (DTI)", _fmt_pct(debt_ratio))
    t.add_row("LTV ratio", _fmt_pct(result.ltv_ratio))
    console.print(t)


def display_amortization(result: OptimizedResult) -> None:
    schedule = build_amortization_schedule(
        result.plan.loan_principal,
        result.plan.annual_interest_rate,
        result.plan.annual_insurance_rate,
        result.loan_duration_months,
    )
    cur = result.currency

    t = Table(title="Amortization Schedule", box=box.MINIMAL_HEAVY_HEAD)
    for col in ("Period", "Opening Bal.", "Installment", "Principal", "Interest", "Insurance", "Closing Bal."):
        t.add_column(col, justify="right")

    for row in schedule:
        t.add_row(
            str(row.period),
            _fmt_money(row.opening_balance, cur),
            _fmt_money(row.monthly_installment, cur),
            _fmt_money(row.principal_component, cur),
            _fmt_money(row.interest_component, cur),
            _fmt_money(row.insurance_component, cur),
            _fmt_money(row.closing_balance, cur),
        )
    console.print(t)


def _fmt_k(value: Decimal) -> str:
    """Format a monetary amount as compact integer (no currency, no decimals)."""
    return f"{value:,.0f}"


def display_sweet_spot(analysis: SweetSpotAnalysis, currency: str) -> None:
    console.print()
    console.print(Panel(
        f"[bold yellow]Down Payment Sweet-Spot Analysis[/bold yellow] "
        f"— {_fmt_months(analysis.duration_months)} — all amounts in {currency}",
        expand=False,
    ))

    # --- Marginal economics header ---
    yield_pct = f"{float(analysis.effective_annual_yield) * 100:.2f}%"
    opp_pct   = f"{float(analysis.opportunity_cost_rate)  * 100:.1f}%"
    saving_k  = _fmt_k(analysis.marginal_saving_per_1k)
    verdict = (
        "[green]EFFICIENT — mortgage beats the market[/green]"
        if analysis.down_payment_is_efficient
        else "[yellow]INEFFICIENT — market beats the mortgage[/yellow]"
    )
    console.print(
        f"  Marginal saving per extra 1 000 {currency} of down payment: "
        f"[bold]{saving_k} {currency}[/bold] in total cost over the loan term\n"
        f"  Effective yield (loan APR):  [bold]{yield_pct}[/bold]   "
        f"Reference rate (opportunity cost): [bold]{opp_pct}[/bold]   {verdict}"
    )

    # --- Milestone table ---
    t = Table(box=box.SIMPLE_HEAVY, show_header=True, padding=(0, 1), expand=False)
    t.add_column("Milestone", style="cyan", min_width=14, max_width=20)
    t.add_column("Down pmt", justify="right", min_width=9)
    t.add_column("Rate", justify="right", min_width=6)
    t.add_column("Monthly", justify="right", min_width=7)
    t.add_column("DTI", justify="right", min_width=4)
    t.add_column("LTV", justify="right", min_width=4)
    t.add_column("Total cost", justify="right", min_width=10)
    t.add_column("Liquidity", justify="right", min_width=9)

    for m in analysis.milestones:
        label = f"[bold green]{m.label}[/bold green]" if m.is_sweet_spot else m.label
        t.add_row(
            label,
            _fmt_k(m.down_payment),
            f"{float(m.effective_rate) * 100:.2f}%",
            _fmt_k(m.plan.monthly_installment),
            f"{float(m.dti_ratio) * 100:.0f}%",
            f"{float(m.ltv_ratio) * 100:.0f}%",
            _fmt_k(m.plan.total_cost_of_credit),
            _fmt_k(m.savings_remaining),
        )

    console.print(t)
    console.print(f"[bold]Verdict:[/bold] {analysis.sweet_spot_reason}")
    if analysis.reserve_warning:
        console.print(f"[yellow]{analysis.reserve_warning}[/yellow]")
    console.print()


def display_params(inputs: UserInputs, params: ResolvedParams) -> None:
    t = Table(title="Current Parameters", box=box.SIMPLE, show_header=True, padding=(0, 2))
    t.add_column("Parameter", style="cyan")
    t.add_column("Value", justify="right")
    t.add_column("Source", style="dim")

    cur = params.currency

    def row(name: str, value: str, source: str = "") -> None:
        t.add_row(name, value, source)

    row("property_price", _fmt_money(params.property_price, cur))
    row("country", params.country, "user" if inputs.country else "default")
    row("profile_quality", params.profile_quality, "user" if inputs.profile_quality else "default")
    row("purchase_taxes", _fmt_money(params.purchase_taxes, cur), params.sources.get("purchase_taxes", ""))
    row("total_acquisition_cost", _fmt_money(params.total_acquisition_cost, cur), "derived")
    row("annual_interest_rate", _fmt_pct(params.annual_interest_rate), params.sources.get("annual_interest_rate", ""))
    row("insurance_rate", _fmt_pct(params.insurance_rate), params.sources.get("insurance_rate", ""))
    row("min_down_payment_ratio", _fmt_pct(params.min_down_payment_ratio), params.sources.get("min_down_payment_ratio", ""))
    row("max_loan_duration_months", str(params.max_loan_duration_months), params.sources.get("max_loan_duration_months", ""))
    if params.fixed_loan_duration_months is not None:
        row("fixed_loan_duration_months", _fmt_months(params.fixed_loan_duration_months), "user")
    row("monthly_net_income", _fmt_money(params.monthly_net_income, cur))
    row("available_savings", _fmt_money(params.available_savings, cur))
    row("max_debt_ratio", _fmt_pct(params.max_debt_ratio), params.sources.get("max_debt_ratio", ""))
    row("max_monthly_payment", _fmt_money(params.max_monthly_payment, cur), params.sources.get("max_monthly_payment", ""))
    row("optimization_preference", inputs.optimization_preference)
    console.print(t)


# ──────────────────────────────────────────────────────────────────────────────
# Input helpers
# ──────────────────────────────────────────────────────────────────────────────

def _prompt_decimal(prompt: str, *, positive: bool = True, allow_zero: bool = False) -> Decimal:
    while True:
        raw = console.input(f"[bold]{prompt}[/bold] ").strip()
        try:
            value = Decimal(raw.replace(",", ".").replace(" ", ""))
        except InvalidOperation:
            err_console.print(f"  Invalid number: '{raw}'")
            continue
        if positive and value <= 0 and not (allow_zero and value == 0):
            err_console.print("  Value must be > 0." if not allow_zero else "  Value must be >= 0.")
            continue
        if allow_zero and value < 0:
            err_console.print("  Value must be >= 0.")
            continue
        return value


def _prompt_int(prompt: str, *, min_val: int = 1) -> int:
    while True:
        raw = console.input(f"[bold]{prompt}[/bold] ").strip()
        try:
            value = int(raw)
        except ValueError:
            err_console.print(f"  Invalid integer: '{raw}'")
            continue
        if value < min_val:
            err_console.print(f"  Value must be >= {min_val}.")
            continue
        return value


def _prompt_country() -> str:
    while True:
        raw = console.input(
            f"[bold]Country code ({', '.join(sorted(SUPPORTED_COUNTRIES))}): [/bold]"
        ).strip().upper()
        if raw in SUPPORTED_COUNTRIES:
            return raw
        err_console.print(f"  Unsupported country '{raw}'.")


def _prompt_quality() -> str:
    while True:
        raw = console.input("[bold]Profile quality (average / best): [/bold]").strip().lower()
        if raw in ("average", "best"):
            return raw
        err_console.print("  Enter 'average' or 'best'.")


def _prompt_preference() -> str:
    prefs = sorted(VALID_PREFERENCES)
    console.print("  Preferences: " + ", ".join(prefs))
    while True:
        raw = console.input("[bold]Optimization preference: [/bold]").strip().lower()
        if raw in VALID_PREFERENCES:
            return raw
        err_console.print(f"  Unknown preference '{raw}'.")


# ──────────────────────────────────────────────────────────────────────────────
# Simulation runner
# ──────────────────────────────────────────────────────────────────────────────

def run_simulation(inputs: UserInputs, store: SessionProfileStore) -> Optional[tuple[ResolvedParams, OptimizedResult]]:
    """Resolve, check feasibility, optimize. Prints errors and returns None on failure."""
    try:
        params = resolve(inputs, store)
    except ValueError as exc:
        err_console.print(f"Parameter error: {exc}")
        return None

    try:
        check_feasibility(params)
    except InfeasibleError as exc:
        console.print(Panel(f"[bold red]Ineligible[/bold red]\n{exc}", expand=False))
        return None

    try:
        result = optimize(params)
    except ValueError as exc:
        console.print(Panel(f"[bold red]No feasible plan found[/bold red]\n{exc}", expand=False))
        return None

    display_result(result)
    return params, result


# ──────────────────────────────────────────────────────────────────────────────
# Country profile update flows
# ──────────────────────────────────────────────────────────────────────────────

def _update_profile_manual(store: SessionProfileStore) -> None:
    country = _prompt_country()
    console.print(
        "  Fields: annual_rate, insurance_rate, purchase_tax_rate, "
        "taxes_financeable, min_down_payment_ratio, max_debt_ratio, max_loan_duration_months"
    )
    field = console.input("[bold]Field to update: [/bold]").strip().lower()

    if field == "annual_rate":
        quality = _prompt_quality()
        value = _prompt_decimal("New annual rate (e.g. 0.035 for 3.5%):", allow_zero=False, positive=True)
        try:
            store.set_annual_rate(country, quality, value, manual=True)  # type: ignore[arg-type]
            console.print(f"  [green]Updated {country} {quality} annual_rate to {_fmt_pct(value)}[/green]")
        except ValueError as exc:
            err_console.print(str(exc))

    elif field == "insurance_rate":
        quality = _prompt_quality()
        value = _prompt_decimal("New insurance rate (e.g. 0.003 for 0.3%):", allow_zero=True, positive=False)
        try:
            store.set_insurance_rate(country, quality, value)  # type: ignore[arg-type]
            console.print(f"  [green]Updated {country} {quality} insurance_rate to {_fmt_pct(value)}[/green]")
        except ValueError as exc:
            err_console.print(str(exc))

    elif field == "purchase_tax_rate":
        value = _prompt_decimal("New purchase tax rate (e.g. 0.075 for 7.5%):", allow_zero=True, positive=False)
        store.set_field(country, "purchase_tax_rate", value)
        console.print(f"  [green]Updated {country} purchase_tax_rate to {_fmt_pct(value)}[/green]")

    elif field == "taxes_financeable":
        raw = console.input("[bold]Taxes financeable? (true / false): [/bold]").strip().lower()
        if raw not in ("true", "false"):
            err_console.print("  Enter 'true' or 'false'.")
            return
        store.set_field(country, "taxes_financeable", raw == "true")
        console.print(f"  [green]Updated {country} taxes_financeable to {raw}[/green]")

    elif field == "min_down_payment_ratio":
        value = _prompt_decimal("New min down payment ratio (e.g. 0.20 for 20%):", allow_zero=True, positive=False)
        store.set_field(country, "min_down_payment_ratio", value)
        console.print(f"  [green]Updated {country} min_down_payment_ratio to {_fmt_pct(value)}[/green]")

    elif field == "max_debt_ratio":
        value = _prompt_decimal("New max debt ratio (e.g. 0.35 for 35%):", allow_zero=False, positive=True)
        store.set_field(country, "max_debt_ratio", value)
        console.print(f"  [green]Updated {country} max_debt_ratio to {_fmt_pct(value)}[/green]")

    elif field == "max_loan_duration_months":
        value_int = _prompt_int("New max loan duration (months, 12–600):", min_val=12)
        if value_int > 600:
            err_console.print("  Max duration cannot exceed 600 months.")
            return
        store.set_field(country, "max_loan_duration_months", value_int)
        console.print(f"  [green]Updated {country} max_loan_duration_months to {value_int}[/green]")

    else:
        err_console.print(f"  Unknown field '{field}'.")


def _update_profile_online(store: SessionProfileStore, inputs: UserInputs) -> None:
    country = _prompt_country()
    console.print(f"  Fetching latest average annual rate for {country}…")
    try:
        fetched = fetch_rate(country)
    except FetchError as exc:
        err_console.print(f"  Fetch failed: {exc}")
        raw = console.input("[bold]Fall back to manual entry? (y/n): [/bold]").strip().lower()
        if raw == "y":
            _update_profile_manual(store)
        return

    quality = "average"
    currently_manual = store.is_annual_rate_manually_set(country, quality)
    current = store.get_annual_rate(country, quality)

    if currently_manual:
        console.print(
            f"  Fetched rate: [bold]{_fmt_pct(fetched)}[/bold]  "
            f"(current override: {_fmt_pct(current)})"
        )
        confirm = console.input("[bold]Replace current override? (y/n): [/bold]").strip().lower()
        if confirm != "y":
            console.print("  Keeping current value.")
            return

    try:
        store.set_annual_rate(country, quality, fetched, manual=False)
        console.print(f"  [green]Applied fetched rate: {_fmt_pct(fetched)} for {country} {quality}[/green]")
    except ValueError as exc:
        err_console.print(str(exc))


# ──────────────────────────────────────────────────────────────────────────────
# Interactive update loop (§5.2)
# ──────────────────────────────────────────────────────────────────────────────

_UPDATABLE_FIELDS = {
    "property_price", "country", "profile_quality", "purchase_taxes",
    "annual_interest_rate", "insurance_rate", "min_down_payment_ratio",
    "max_loan_duration_months", "fixed_loan_duration_months",
    "monthly_net_income", "available_savings",
    "max_debt_ratio", "max_monthly_payment", "optimization_preference",
}


def interactive_loop(inputs: UserInputs, store: SessionProfileStore) -> None:
    last_params: Optional[ResolvedParams] = None
    last_result: Optional[OptimizedResult] = None

    result = run_simulation(inputs, store)
    if result:
        last_params, last_result = result

    while True:
        console.print()
        console.print(
            "[bold]Actions:[/bold] "
            "[cyan]update[/cyan] · [cyan]reset[/cyan] · [cyan]profile[/cyan] · "
            "[cyan]schedule[/cyan] · [cyan]sweetspot[/cyan] · [cyan]params[/cyan] · [cyan]exit[/cyan]"
        )
        action = console.input("[bold]> [/bold]").strip().lower()

        if action in ("exit", "quit", "q"):
            console.print("Goodbye.")
            break

        elif action == "params":
            if last_params:
                display_params(inputs, last_params)
            else:
                err_console.print("No simulation result available yet.")

        elif action == "schedule":
            if last_result:
                display_amortization(last_result)
            else:
                err_console.print("Run a simulation first.")

        elif action == "sweetspot":
            if last_params is None:
                err_console.print("Run a simulation first.")
            else:
                try:
                    analysis = analyze_sweet_spot(last_params)
                    display_sweet_spot(analysis, last_params.currency)
                except Exception as exc:
                    err_console.print(f"Sweet-spot analysis failed: {exc}")

        elif action == "update":
            console.print(f"  Fields: {', '.join(sorted(_UPDATABLE_FIELDS))}")
            field = console.input("[bold]Field to update: [/bold]").strip().lower()
            if field not in _UPDATABLE_FIELDS:
                err_console.print(f"  Unknown field '{field}'.")
                continue

            _apply_update(field, inputs, store)
            result = run_simulation(inputs, store)
            if result:
                last_params, last_result = result

        elif action == "reset":
            console.print(f"  Fields: {', '.join(sorted(_UPDATABLE_FIELDS))}")
            field = console.input("[bold]Field to reset to profile default: [/bold]").strip().lower()
            _reset_field(field, inputs)
            result = run_simulation(inputs, store)
            if result:
                last_params, last_result = result

        elif action == "profile":
            mode = console.input("[bold]Update mode (manual / online): [/bold]").strip().lower()
            if mode == "manual":
                _update_profile_manual(store)
            elif mode == "online":
                _update_profile_online(store, inputs)
            else:
                err_console.print("  Enter 'manual' or 'online'.")
                continue
            result = run_simulation(inputs, store)
            if result:
                last_params, last_result = result

        else:
            err_console.print(f"  Unknown action '{action}'.")


def _apply_update(field: str, inputs: UserInputs, store: SessionProfileStore) -> None:
    try:
        if field == "property_price":
            inputs.property_price = _prompt_decimal("New property price:", positive=True)
        elif field == "country":
            inputs.country = _prompt_country()
        elif field == "profile_quality":
            inputs.profile_quality = _prompt_quality()  # type: ignore[assignment]
        elif field == "purchase_taxes":
            inputs.purchase_taxes = _prompt_decimal("New purchase taxes:", allow_zero=True, positive=False)
        elif field == "annual_interest_rate":
            inputs.annual_interest_rate = _prompt_decimal(
                "New annual interest rate (e.g. 0.035):", positive=True
            )
        elif field == "insurance_rate":
            inputs.insurance_rate = _prompt_decimal(
                "New insurance rate (e.g. 0.003):", allow_zero=True, positive=False
            )
        elif field == "min_down_payment_ratio":
            inputs.min_down_payment_ratio = _prompt_decimal(
                "New min down payment ratio (e.g. 0.20):", allow_zero=True, positive=False
            )
        elif field == "max_loan_duration_months":
            inputs.max_loan_duration_months = _prompt_int("New max loan duration (months):", min_val=12)
        elif field == "fixed_loan_duration_months":
            inputs.fixed_loan_duration_months = _prompt_int("Fixed loan duration (months, e.g. 240 for 20y):", min_val=12)
        elif field == "monthly_net_income":
            inputs.monthly_net_income = _prompt_decimal("New monthly net income:", positive=True)
        elif field == "available_savings":
            inputs.available_savings = _prompt_decimal("New available savings:", allow_zero=True, positive=False)
        elif field == "max_debt_ratio":
            inputs.max_debt_ratio = _prompt_decimal(
                "New max debt ratio (e.g. 0.35 for 35%):", allow_zero=False, positive=True
            )
        elif field == "max_monthly_payment":
            inputs.max_monthly_payment = _prompt_decimal("New max monthly payment:", positive=True)
        elif field == "optimization_preference":
            inputs.optimization_preference = _prompt_preference()
    except (KeyboardInterrupt, EOFError):
        console.print("\n  Update cancelled.")


def _reset_field(field: str, inputs: UserInputs) -> None:
    if field == "country":
        inputs.country = None
    elif field == "profile_quality":
        inputs.profile_quality = None
    elif field == "purchase_taxes":
        inputs.purchase_taxes = None
    elif field == "annual_interest_rate":
        inputs.annual_interest_rate = None
    elif field == "insurance_rate":
        inputs.insurance_rate = None
    elif field == "min_down_payment_ratio":
        inputs.min_down_payment_ratio = None
    elif field == "max_loan_duration_months":
        inputs.max_loan_duration_months = None
    elif field == "fixed_loan_duration_months":
        inputs.fixed_loan_duration_months = None
    elif field == "max_debt_ratio":
        inputs.max_debt_ratio = None
    elif field == "max_monthly_payment":
        inputs.max_monthly_payment = None
    elif field == "optimization_preference":
        inputs.optimization_preference = "balanced"
    else:
        err_console.print(f"  Field '{field}' cannot be reset (it is mandatory or derived).")


# ──────────────────────────────────────────────────────────────────────────────
# Click entry point
# ──────────────────────────────────────────────────────────────────────────────

@click.command()
@click.option("--property-price", type=str, default=None, help="Property price")
@click.option("--income", type=str, default=None, help="Monthly net income")
@click.option("--savings", type=str, default=None, help="Available savings")
@click.option("--purchase-taxes", type=str, default=None, help="Purchase taxes (overrides profile estimate)")
@click.option("--country", type=str, default=None, help=f"Country code (default: {DEFAULT_COUNTRY})")
@click.option("--quality", type=click.Choice(["average", "best"]), default=None, help="Profile quality")
@click.option("--preference", type=click.Choice(list(VALID_PREFERENCES)), default="balanced", show_default=True)
@click.option("--duration", type=str, default=None, help="Pin loan duration: months (e.g. 240) or years (e.g. 20y). Omit to let the optimizer search freely.")
def main(
    property_price: Optional[str],
    income: Optional[str],
    savings: Optional[str],
    purchase_taxes: Optional[str],
    country: Optional[str],
    quality: Optional[str],
    preference: str,
    duration: Optional[str],
) -> None:
    """Interactive credit / mortgage loan simulator."""
    console.print(Panel("[bold blue]Credit Simulator[/bold blue]", expand=False))

    store = SessionProfileStore()

    def _parse_opt(s: Optional[str], name: str) -> Optional[Decimal]:
        if s is None:
            return None
        try:
            return Decimal(s.replace(",", ".").replace(" ", ""))
        except InvalidOperation:
            err_console.print(f"Invalid value for --{name}: '{s}'")
            sys.exit(1)

    # Collect mandatory fields (from CLI args or interactive prompt)
    pp = _parse_opt(property_price, "property-price")
    if pp is None:
        pp = _prompt_decimal("Property price?", positive=True)

    inc = _parse_opt(income, "income")
    if inc is None:
        inc = _prompt_decimal("Monthly net income?", positive=True)

    sav = _parse_opt(savings, "savings")
    if sav is None:
        sav = _prompt_decimal("Available savings?", allow_zero=True, positive=False)

    pt = _parse_opt(purchase_taxes, "purchase-taxes")
    if pt is None:
        raw_pt = console.input(
            "[bold]Purchase taxes? (press Enter to estimate from country profile): [/bold]"
        ).strip()
        if raw_pt:
            try:
                pt = Decimal(raw_pt.replace(",", ".").replace(" ", ""))
            except InvalidOperation:
                err_console.print(f"  Invalid number: '{raw_pt}'. Will estimate from profile.")

    fixed_duration: Optional[int] = None
    if duration is not None:
        raw_dur = duration.strip().lower()
        try:
            if raw_dur.endswith("y"):
                fixed_duration = int(raw_dur[:-1]) * 12
            else:
                fixed_duration = int(raw_dur)
        except ValueError:
            err_console.print(f"Invalid --duration value '{duration}'. Use months (e.g. 240) or years (e.g. 20y).")
            sys.exit(1)
        if fixed_duration < 12:
            err_console.print("--duration must be at least 12 months.")
            sys.exit(1)

    inputs = UserInputs(
        property_price=pp,
        monthly_net_income=inc,
        available_savings=sav,
        purchase_taxes=pt,
        country=country,
        profile_quality=quality,  # type: ignore[arg-type]
        optimization_preference=preference,
        fixed_loan_duration_months=fixed_duration,
    )

    try:
        interactive_loop(inputs, store)
    except (KeyboardInterrupt, EOFError):
        console.print("\nSession ended.")
