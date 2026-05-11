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

import contextlib
import sys
from decimal import ROUND_HALF_UP as _ROUND_HALF_UP
from decimal import Decimal, InvalidOperation

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import preferences
from .calculator import build_amortization_schedule
from .config import (
    DEFAULT_COUNTRY,
    DEFAULT_LOAN_DURATION_MONTHS,
    SWEET_SPOT_OPPORTUNITY_COST_RATE,
    VALID_PREFERENCES,
)
from .fetcher import FetchError, fetch_rate
from .i18n import _, detect_locale, set_locale
from .optimizer import (
    OptimizedResult,
    SweetSpotAnalysis,
    analyze_sweet_spot,
    optimize,
)
from .profiles import (
    SUPPORTED_COUNTRIES,
    SessionProfileStore,
)
from .resolver import InfeasibleError, ResolvedParams, UserInputs, check_feasibility, resolve

console = Console()
err_console = Console(stderr=True, style="bold red")


def _is_yes(raw: str) -> bool:
    """Accept affirmative answers in English and French."""
    return raw.lower() in ("y", "yes", "o", "oui", "")


def _is_explicit_yes(raw: str) -> bool:
    """Like _is_yes but does NOT accept the empty string."""
    return raw.lower() in ("y", "yes", "o", "oui")


# ──────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ──────────────────────────────────────────────────────────────────────────────

def _fmt_money(value: Decimal, currency: str) -> str:
    return f"{value:,.2f} {currency}"


def _fmt_pct(value: Decimal) -> str:
    return f"{value * Decimal('100'):.4f}%"


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
        _(
            "panel.optimal_plan",
            country=result.country,
            quality=result.profile_quality,
            preference=result.optimization_preference,
        ),
        expand=False,
    ))

    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    t.add_column("Field", style="cyan")
    t.add_column("Value", justify="right")

    plan = result.plan
    t.add_row(_("label.down_payment"), _fmt_money(result.down_payment, cur))
    t.add_row(_("label.loan_principal"), _fmt_money(result.loan_principal, cur))
    t.add_row(_("label.loan_duration"), _fmt_months(result.loan_duration_months))
    t.add_row(_("label.monthly_installment"), _fmt_money(plan.monthly_installment, cur))
    t.add_row(_("label.emi"), _fmt_money(plan.monthly_emi, cur))
    t.add_row(_("label.insurance"), _fmt_money(plan.monthly_insurance, cur))
    t.add_row(_("label.first_month_interest"), _fmt_money(plan.monthly_interest_first, cur))
    t.add_row(_("label.apr"), _fmt_pct(plan.effective_annual_rate))
    t.add_row(_("label.total_interest"), _fmt_money(plan.total_interest_paid, cur))
    t.add_row(_("label.total_insurance"), _fmt_money(plan.total_insurance_paid, cur))
    t.add_row(_("label.total_cost"), _fmt_money(plan.total_cost_of_credit, cur))
    t.add_row(_("label.total_repaid"), _fmt_money(plan.total_repaid, cur))
    debt_ratio = plan.monthly_installment / result.monthly_net_income
    t.add_row(_("label.dti"), _fmt_pct(debt_ratio))
    t.add_row(_("label.ltv"), _fmt_pct(result.ltv_ratio))
    console.print(t)


def display_amortization(result: OptimizedResult) -> None:
    with console.status(_("status.generating_schedule")):
        schedule = build_amortization_schedule(
            result.plan.loan_principal,
            result.plan.annual_interest_rate,
            result.plan.annual_insurance_rate,
            result.loan_duration_months,
        )
    cur = result.currency

    t = Table(title=_("table.amortization"), box=box.MINIMAL_HEAVY_HEAD)
    for col in (
        _("col.period"), _("col.opening_bal"), _("col.installment"),
        _("col.principal"), _("col.interest"), _("col.insurance"), _("col.closing_bal"),
    ):
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
        _(
            "panel.sweet_spot",
            duration=_fmt_months(analysis.duration_months),
            currency=currency,
        ),
        expand=False,
    ))

    # --- Marginal economics header ---
    yield_pct = f"{analysis.effective_annual_yield * Decimal('100'):.2f}%"
    opp_pct   = f"{analysis.opportunity_cost_rate * Decimal('100'):.1f}%"
    saving_k  = _fmt_k(analysis.marginal_saving_per_1k)
    verdict = (
        _("sweetspot.verdict.efficient")
        if analysis.down_payment_is_efficient
        else _("sweetspot.verdict.inefficient")
    )
    console.print(_(
        "sweetspot.marginal_saving", saving=saving_k, currency=currency
    ))
    console.print(_(
        "sweetspot.yield_line",
        yield_pct=yield_pct,
        opp_pct=opp_pct,
        verdict=verdict,
    ))
    console.print(_("sweetspot.crossover_dim", note=analysis.crossover_note))

    # --- Milestone table ---
    t = Table(box=box.SIMPLE_HEAVY, show_header=True, padding=(0, 1), expand=False)
    t.add_column(_("sweetspot.col.milestone"), style="cyan", min_width=18, max_width=28)
    t.add_column(_("sweetspot.col.down_pmt"),  justify="right", min_width=9)
    t.add_column(_("sweetspot.col.rate"),      justify="right", min_width=6)
    t.add_column(_("sweetspot.col.monthly"),   justify="right", min_width=7)
    t.add_column(_("sweetspot.col.dti"),       justify="right", min_width=4)
    t.add_column(_("sweetspot.col.ltv"),       justify="right", min_width=4)
    t.add_column(_("sweetspot.col.total_cost"),justify="right", min_width=10)
    t.add_column(_("sweetspot.col.liquidity"), justify="right", min_width=9)

    for m in analysis.milestones:
        if m.is_sweet_spot:
            label = f"[bold green]{m.label}[/bold green]"
        elif m.is_rate_floor:
            label = f"[bold magenta]{m.label}[/bold magenta]"
        elif m.is_user_choice:
            label = f"[bold cyan]{m.label}[/bold cyan]"
        else:
            label = m.label
        t.add_row(
            label,
            _fmt_k(m.down_payment),
            f"{m.effective_rate * Decimal('100'):.2f}%",
            _fmt_k(m.plan.monthly_installment),
            f"{m.dti_ratio * Decimal('100'):.0f}%",
            f"{m.ltv_ratio * Decimal('100'):.0f}%",
            _fmt_k(m.plan.total_cost_of_credit),
            _fmt_k(m.savings_remaining),
        )

    console.print(t)
    console.print(_("sweetspot.verdict_line", reason=analysis.sweet_spot_reason))
    if analysis.reserve_warning:
        console.print(f"[yellow]{analysis.reserve_warning}[/yellow]")

    # --- Per-tier economics table ---
    if analysis.tier_economics:
        console.print()
        console.print(_("sweetspot.tier_header", currency=currency))
        te = Table(box=box.SIMPLE, show_header=True, padding=(0, 1), expand=False)
        te.add_column(_("sweetspot.col.ltv_tier"), style="dim", min_width=10)
        te.add_column(_("sweetspot.col.rate"),     justify="right", min_width=8)
        te.add_column(_("sweetspot.col.delta"),    justify="right", min_width=7)
        te.add_column(_("sweetspot.col.saves"),    justify="right", min_width=12)
        te.add_column(_("sweetspot.col.yield"),    justify="right", min_width=6)
        for tier in analysis.tier_economics:
            rate_str = f"{tier.effective_rate * Decimal('100'):.2f}%"
            save_str = f"{_fmt_k(tier.saving_per_1k)} {currency}"
            yield_str = f"{tier.annual_yield * Decimal('100'):.2f}%"
            if tier.is_best_tier:
                te.add_row(
                    f"[magenta]{tier.ltv_range}[/magenta]",
                    f"[magenta]{rate_str}[/magenta]",
                    f"[magenta]{tier.rate_delta_label}[/magenta]",
                    f"[magenta]{save_str}[/magenta]",
                    f"[magenta]{yield_str}[/magenta]",
                )
            else:
                te.add_row(tier.ltv_range, rate_str, tier.rate_delta_label, save_str, yield_str)
        console.print(te)
        console.print(_("sweetspot.tier_footnote"))

    console.print()


def _display_profile_summary(store: SessionProfileStore, country: str) -> None:
    """Show a compact profile defaults box so users know what they'll get."""
    cur = str(store.get_field(country, "currency"))
    avg_rate = store.get_annual_rate(country, "average")
    best_rate = store.get_annual_rate(country, "best")
    avg_ins = store.get_insurance_rate(country, "average")
    best_ins = store.get_insurance_rate(country, "best")
    tax_rate = Decimal(str(store.get_field(country, "purchase_tax_rate")))
    min_dp = Decimal(str(store.get_field(country, "min_down_payment_ratio")))
    max_debt = Decimal(str(store.get_field(country, "max_debt_ratio")))
    max_dur = int(store.get_field(country, "max_loan_duration_months"))
    taxes_fin = bool(store.get_field(country, "taxes_financeable"))
    console.print(Panel(
        _(
            "profile.summary",
            country=country,
            currency=cur,
            avg_rate=_fmt_pct(avg_rate),
            best_rate=_fmt_pct(best_rate),
            avg_ins=_fmt_pct(avg_ins),
            best_ins=_fmt_pct(best_ins),
            tax_rate=_fmt_pct(tax_rate),
            financed=_("profile.yes") if taxes_fin else _("profile.no"),
            min_dp=_fmt_pct(min_dp),
            max_dti=_fmt_pct(max_debt),
            max_dur=max_dur // 12,
        ),
        title=_("panel.country_defaults"),
        expand=False,
    ))



def display_params(inputs: UserInputs, params: ResolvedParams) -> None:
    t = Table(
        title=_("table.current_params"),
        box=box.SIMPLE,
        show_header=True,
        padding=(0, 2),
    )
    t.add_column(_("table.col.parameter"), style="cyan")
    t.add_column(_("table.col.value"), justify="right")
    t.add_column(_("table.col.source"), style="dim")

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
    row("fixed_loan_duration_months", _fmt_months(params.fixed_loan_duration_months), params.sources.get("fixed_loan_duration_months", "default"))
    row("monthly_net_income", _fmt_money(params.monthly_net_income, cur))
    row("available_savings", _fmt_money(params.available_savings, cur))
    if params.preferred_down_payment is not None:
        row("preferred_down_payment", _fmt_money(params.preferred_down_payment, cur), params.sources.get("preferred_down_payment", "user"))
    row("max_debt_ratio", _fmt_pct(params.max_debt_ratio), params.sources.get("max_debt_ratio", ""))
    row("max_monthly_payment", _fmt_money(params.max_monthly_payment, cur), params.sources.get("max_monthly_payment", ""))
    row("optimization_preference", inputs.optimization_preference)
    opp_src = "user" if inputs.opportunity_cost_rate is not None else "default"
    row("opportunity_cost_rate", _fmt_pct(params.opportunity_cost_rate), opp_src)
    console.print(t)


# ──────────────────────────────────────────────────────────────────────────────
# Input helpers
# ──────────────────────────────────────────────────────────────────────────────

def _prompt_decimal(
    prompt: str,
    *,
    positive: bool = True,
    allow_zero: bool = False,
    hint: str = "",
    help_text: str = "",
) -> Decimal:
    """Prompt for a Decimal value.  Type '?' for inline help."""
    display = f"{prompt} [{hint}]" if hint else prompt
    while True:
        raw = console.input(f"[bold]{display}[/bold] ").strip()
        if raw == "?":
            console.print(f"  [dim]{help_text or _('error.no_help')}[/dim]")
            continue
        try:
            value = Decimal(raw.replace(",", ".").replace(" ", ""))
        except InvalidOperation:
            err_console.print(_("error.invalid_number", val=raw))
            continue
        if positive and value <= 0 and not (allow_zero and value == 0):
            err_console.print(_("error.must_be_positive") if not allow_zero else _("error.must_be_nonneg"))
            continue
        if allow_zero and value < 0:
            err_console.print(_("error.must_be_nonneg"))
            continue
        return value


def _prompt_decimal_with_default(
    prompt: str,
    default: Decimal,
    *,
    positive: bool = True,
    allow_zero: bool = False,
) -> Decimal:
    """Prompt for a Decimal, accepting Enter to keep *default*."""
    while True:
        raw = console.input(
            f"[bold]{prompt} [dim][saved: {default}][/dim][/bold] "
        ).strip()
        if not raw:
            return default
        try:
            value = Decimal(raw.replace(",", ".").replace(" ", ""))
        except InvalidOperation:
            err_console.print(_("error.invalid_number", val=raw))
            continue
        if positive and value <= 0 and not (allow_zero and value == 0):
            err_console.print(_("error.must_be_positive") if not allow_zero else _("error.must_be_nonneg"))
            continue
        if allow_zero and value < 0:
            err_console.print(_("error.must_be_nonneg"))
            continue
        return value


def _prompt_int(
    prompt: str,
    *,
    min_val: int = 1,
    hint: str = "",
    help_text: str = "",
) -> int:
    """Prompt for an integer value.  Type '?' for inline help."""
    display = f"{prompt} [{hint}]" if hint else prompt
    while True:
        raw = console.input(f"[bold]{display}[/bold] ").strip()
        if raw == "?":
            console.print(f"  [dim]{help_text or _('error.no_help')}[/dim]")
            continue
        try:
            value = int(raw)
        except ValueError:
            err_console.print(_("error.invalid_integer", val=raw))
            continue
        if value < min_val:
            err_console.print(_("error.must_be_at_least", min_val=min_val))
            continue
        return value


def _prompt_country() -> str:
    while True:
        raw = console.input(
            f"[bold]{_('prompt.country', countries=', '.join(sorted(SUPPORTED_COUNTRIES)))}[/bold]"
        ).strip().upper()
        if raw in SUPPORTED_COUNTRIES:
            return raw
        err_console.print(_("error.unsupported_country", country=raw))


def _prompt_quality() -> str:
    while True:
        raw = console.input(f"[bold]{_('prompt.quality')}[/bold]").strip().lower()
        if raw in ("average", "best"):
            return raw
        err_console.print(_("error.enter_average_best"))


def _prompt_preference() -> str:
    prefs = sorted(VALID_PREFERENCES)
    console.print(_("action.preferences_list", prefs=", ".join(prefs)))
    while True:
        raw = console.input(f"[bold]{_('prompt.preference')}[/bold]").strip().lower()
        if raw in VALID_PREFERENCES:
            return raw
        err_console.print(_("error.unknown_preference", pref=raw))


# ──────────────────────────────────────────────────────────────────────────────
# Simulation runner
# ──────────────────────────────────────────────────────────────────────────────

def run_simulation(inputs: UserInputs, store: SessionProfileStore) -> tuple | None:
    """Resolve, check feasibility, optimize, and show sweet-spot analysis.

    Returns (params, result, analysis) on success, or None on any failure.
    analysis may be None if the sweet-spot computation itself fails.
    """
    try:
        with console.status(_("status.resolving")):
            params = resolve(inputs, store)
    except ValueError as exc:
        err_console.print(_("error.param_error", exc=exc))
        return None

    try:
        check_feasibility(params)
    except InfeasibleError as exc:
        console.print(Panel(_("panel.ineligible", exc=exc), expand=False))
        return None

    try:
        with console.status(_("status.optimizing")):
            result = optimize(params)
    except ValueError as exc:
        console.print(Panel(_("panel.no_plan", exc=exc), expand=False))
        return None

    display_result(result)

    analysis: SweetSpotAnalysis | None = None
    try:
        with console.status(_("status.sweet_spot")):
            analysis = analyze_sweet_spot(params)
        display_sweet_spot(analysis, params.currency)
    except Exception as exc:
        err_console.print(_("error.sweet_spot_failed", exc=exc))

    return params, result, analysis


# ──────────────────────────────────────────────────────────────────────────────
# Country profile update flows
# ──────────────────────────────────────────────────────────────────────────────

def _update_profile_manual(store: SessionProfileStore) -> None:
    country = _prompt_country()
    console.print(_("action.profile_fields"))
    field = console.input(f"[bold]{_('prompt.field_to_update')}[/bold]").strip().lower()

    if field == "annual_rate":
        quality = _prompt_quality()
        value = _prompt_decimal(_("prompt.new_rate"), allow_zero=False, positive=True)
        try:
            store.set_annual_rate(country, quality, value, manual=True)  # type: ignore[arg-type]
            console.print(_("profile.updated", country=country, quality=quality, field="annual_rate", value=_fmt_pct(value)))
        except ValueError as exc:
            err_console.print(str(exc))

    elif field == "insurance_rate":
        quality = _prompt_quality()
        value = _prompt_decimal(_("prompt.new_insurance"), allow_zero=True, positive=False)
        try:
            store.set_insurance_rate(country, quality, value)  # type: ignore[arg-type]
            console.print(_("profile.updated", country=country, quality=quality, field="insurance_rate", value=_fmt_pct(value)))
        except ValueError as exc:
            err_console.print(str(exc))

    elif field == "purchase_tax_rate":
        value = _prompt_decimal(_("prompt.new_tax"), allow_zero=True, positive=False)
        store.set_field(country, "purchase_tax_rate", value)
        console.print(_("profile.updated", country=country, quality="", field="purchase_tax_rate", value=_fmt_pct(value)))

    elif field == "taxes_financeable":
        raw = console.input(f"[bold]{_('prompt.taxes_financeable')}[/bold]").strip().lower()
        if raw not in ("true", "false"):
            err_console.print(_("error.enter_true_false"))
            return
        store.set_field(country, "taxes_financeable", raw == "true")
        console.print(_("profile.updated", country=country, quality="", field="taxes_financeable", value=raw))

    elif field == "min_down_payment_ratio":
        value = _prompt_decimal(_("prompt.new_min_dp"), allow_zero=True, positive=False)
        store.set_field(country, "min_down_payment_ratio", value)
        console.print(_("profile.updated", country=country, quality="", field="min_down_payment_ratio", value=_fmt_pct(value)))

    elif field == "max_debt_ratio":
        value = _prompt_decimal(_("prompt.new_max_debt"), allow_zero=False, positive=True)
        store.set_field(country, "max_debt_ratio", value)
        console.print(_("profile.updated", country=country, quality="", field="max_debt_ratio", value=_fmt_pct(value)))

    elif field == "max_loan_duration_months":
        value_int = _prompt_int(_("prompt.new_max_dur"), min_val=12)
        if value_int > 600:
            err_console.print(_("error.max_duration_exceeded"))
            return
        store.set_field(country, "max_loan_duration_months", value_int)
        console.print(_("profile.updated", country=country, quality="", field="max_loan_duration_months", value=str(value_int)))

    else:
        err_console.print(_("error.unknown_field", field=field))


def _update_profile_online(store: SessionProfileStore, inputs: UserInputs) -> None:
    country = _prompt_country()
    try:
        with console.status(_("status.fetching_rate", country=country)):
            fetched = fetch_rate(country)
    except FetchError as exc:
        err_console.print(_("error.fetch_failed", exc=exc))
        raw = console.input(f"[bold]{_('prompt.fallback_manual')}[/bold]").strip()
        if _is_explicit_yes(raw):
            _update_profile_manual(store)
        return

    quality = "average"
    currently_manual = store.is_annual_rate_manually_set(country, quality)
    current = store.get_annual_rate(country, quality)

    if currently_manual:
        console.print(_("profile.fetched_shown", fetched=_fmt_pct(fetched), current=_fmt_pct(current)))
        confirm = console.input(f"[bold]{_('prompt.replace_override')}[/bold]").strip()
        if not _is_explicit_yes(confirm):
            console.print(_("action.keeping_current"))
            return

    try:
        store.set_annual_rate(country, quality, fetched, manual=False)
        console.print(_("profile.fetched_applied", rate=_fmt_pct(fetched), country=country, quality=quality))
    except ValueError as exc:
        err_console.print(str(exc))


# ──────────────────────────────────────────────────────────────────────────────
# Interactive update loop (§5.2)
# ──────────────────────────────────────────────────────────────────────────────

_UPDATABLE_FIELDS = {
    "property_price", "country", "profile_quality", "purchase_taxes",
    "annual_interest_rate", "insurance_rate", "min_down_payment_ratio",
    "max_loan_duration_months", "fixed_loan_duration_months",
    "monthly_net_income", "available_savings", "preferred_down_payment",
    "max_debt_ratio", "max_monthly_payment", "optimization_preference",
    "opportunity_cost_rate",
}


def interactive_loop(inputs: UserInputs, store: SessionProfileStore) -> None:
    last_params: ResolvedParams | None = None
    last_result: OptimizedResult | None = None
    last_analysis: SweetSpotAnalysis | None = None

    run_result = run_simulation(inputs, store)
    if run_result:
        last_params, last_result, last_analysis = run_result

    while True:
        console.print()
        console.print(_("action.menu"))
        action = console.input(f"[bold]{_('prompt.action')} [/bold]").strip().lower()

        if action in ("exit", "quit", "q"):
            preferences.save(inputs, store)
            console.print(_("action.goodbye"))
            break

        elif action == "params":
            if last_params:
                display_params(inputs, last_params)
            else:
                err_console.print(_("error.no_result"))

        elif action == "schedule":
            if last_result:
                display_amortization(last_result)
            else:
                err_console.print(_("error.run_first"))

        elif action == "sweetspot":
            if last_analysis is not None:
                display_sweet_spot(last_analysis, last_params.currency)
            elif last_params is not None:
                try:
                    with console.status(_("status.sweet_spot")):
                        last_analysis = analyze_sweet_spot(last_params)
                    display_sweet_spot(last_analysis, last_params.currency)
                except Exception as exc:
                    err_console.print(_("error.sweet_spot_failed", exc=exc))
            else:
                err_console.print(_("error.run_first"))

        elif action == "update":
            console.print(_("action.fields_list", fields=", ".join(sorted(_UPDATABLE_FIELDS))))
            field = console.input(f"[bold]{_('prompt.field_to_update')}[/bold]").strip().lower()
            if field not in _UPDATABLE_FIELDS:
                err_console.print(_("error.unknown_field", field=field))
                continue

            _apply_update(field, inputs, store)
            run_result = run_simulation(inputs, store)
            if run_result:
                last_params, last_result, last_analysis = run_result
                preferences.save(inputs, store)

        elif action == "reset":
            console.print(_("action.fields_list", fields=", ".join(sorted(_UPDATABLE_FIELDS))))
            field = console.input(f"[bold]{_('prompt.field_to_reset')}[/bold]").strip().lower()
            _reset_field(field, inputs)
            run_result = run_simulation(inputs, store)
            if run_result:
                last_params, last_result, last_analysis = run_result
                preferences.save(inputs, store)

        elif action == "profile":
            mode = console.input(f"[bold]{_('prompt.update_mode')}[/bold]").strip().lower()
            if mode == "manual":
                _update_profile_manual(store)
            elif mode == "online":
                _update_profile_online(store, inputs)
            else:
                err_console.print(_("error.enter_manual_online"))
                continue
            run_result = run_simulation(inputs, store)
            if run_result:
                last_params, last_result, last_analysis = run_result
                preferences.save(inputs, store)

        else:
            err_console.print(_("error.unknown_action", action=action))


def _apply_update(field: str, inputs: UserInputs, store: SessionProfileStore) -> None:
    try:
        if field == "property_price":
            inputs.property_price = _prompt_decimal(_("prompt.new_property_price"), positive=True)
        elif field == "country":
            inputs.country = _prompt_country()
        elif field == "profile_quality":
            inputs.profile_quality = _prompt_quality()  # type: ignore[assignment]
        elif field == "purchase_taxes":
            inputs.purchase_taxes = _prompt_decimal(_("prompt.new_taxes"), allow_zero=True, positive=False)
        elif field == "annual_interest_rate":
            inputs.annual_interest_rate = _prompt_decimal(_("prompt.new_rate_direct"), positive=True)
        elif field == "insurance_rate":
            inputs.insurance_rate = _prompt_decimal(_("prompt.new_insurance_direct"), allow_zero=True, positive=False)
        elif field == "min_down_payment_ratio":
            inputs.min_down_payment_ratio = _prompt_decimal(_("prompt.new_min_dp_direct"), allow_zero=True, positive=False)
        elif field == "max_loan_duration_months":
            inputs.max_loan_duration_months = _prompt_int(_("prompt.new_max_dur"), min_val=12)
        elif field == "fixed_loan_duration_months":
            inputs.fixed_loan_duration_months = _prompt_int(_("prompt.new_max_dur_direct"), min_val=12)
        elif field == "monthly_net_income":
            inputs.monthly_net_income = _prompt_decimal(_("prompt.new_income"), positive=True)
        elif field == "available_savings":
            inputs.available_savings = _prompt_decimal(_("prompt.new_savings"), allow_zero=True, positive=False)
        elif field == "preferred_down_payment":
            inputs.preferred_down_payment = _prompt_decimal(_("prompt.new_preferred_dp"), allow_zero=True, positive=False)
        elif field == "max_debt_ratio":
            inputs.max_debt_ratio = _prompt_decimal(_("prompt.new_max_debt_direct"), allow_zero=False, positive=True)
        elif field == "max_monthly_payment":
            inputs.max_monthly_payment = _prompt_decimal(_("prompt.new_max_payment"), positive=True)
        elif field == "optimization_preference":
            inputs.optimization_preference = _prompt_preference()
        elif field == "opportunity_cost_rate":
            inputs.opportunity_cost_rate = _prompt_decimal(
                _("prompt.new_opp_rate"),
                positive=True,
                help_text=_("help.opp_rate"),
            )
    except (KeyboardInterrupt, EOFError):
        console.print(_("action.update_cancelled"))


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
    elif field == "preferred_down_payment":
        inputs.preferred_down_payment = None
    elif field == "max_debt_ratio":
        inputs.max_debt_ratio = None
    elif field == "max_monthly_payment":
        inputs.max_monthly_payment = None
    elif field == "optimization_preference":
        inputs.optimization_preference = "balanced"
    elif field == "opportunity_cost_rate":
        inputs.opportunity_cost_rate = None
    else:
        err_console.print(_("error.unknown_field", field=field))


def _apply_saved_optionals(prefs: dict, inputs: UserInputs) -> None:
    """Copy saved optional fields onto *inputs*, skipping any already set by the user."""
    saved = prefs.get("inputs", {})

    for field in ("country", "profile_quality", "optimization_preference"):
        if getattr(inputs, field, None) is None or (
            field == "optimization_preference" and inputs.optimization_preference == "balanced"
            and saved.get(field) not in (None, "balanced")
        ):
            val = saved.get(field)
            if val is not None:
                setattr(inputs, field, val)

    for field in (
        "opportunity_cost_rate", "annual_interest_rate", "insurance_rate",
        "min_down_payment_ratio", "max_debt_ratio", "max_monthly_payment",
    ):
        if getattr(inputs, field, None) is None:
            raw = saved.get(field)
            if raw is not None:
                with contextlib.suppress(InvalidOperation):
                    setattr(inputs, field, Decimal(str(raw)))

    for field in ("max_loan_duration_months", "fixed_loan_duration_months"):
        if getattr(inputs, field, None) is None:
            raw = saved.get(field)
            if raw is not None:
                with contextlib.suppress(TypeError, ValueError):
                    setattr(inputs, field, int(raw))


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
@click.option("--down-payment", type=str, default=None, help="Intended down payment. Omit to let the optimizer find the best.")
@click.option("--duration", type=str, default=None, help="Loan duration: months (e.g. 240) or years (e.g. 20y). Default: 20y.")
@click.option("--opp-rate", type=str, default=None, help="Opportunity-cost rate for sweet-spot analysis (e.g. 0.04 for 4%). Default: 3.5%.")
@click.option("--locale", type=str, default=None, help="Interface language: 'en' or 'fr'. Auto-detected if omitted.")
def main(
    property_price: str | None,
    income: str | None,
    savings: str | None,
    purchase_taxes: str | None,
    country: str | None,
    quality: str | None,
    preference: str,
    down_payment: str | None,
    duration: str | None,
    opp_rate: str | None,
    locale: str | None,
) -> None:
    """Interactive credit / mortgage loan simulator."""
    # Set locale before any output
    set_locale(locale if locale is not None else detect_locale())

    console.print(Panel(_("panel.credit_simulator"), expand=False))

    store = SessionProfileStore()
    prefs = preferences.load()
    preferences.apply_to_store(prefs, store)

    def _parse_opt(s: str | None, name: str) -> Decimal | None:
        if s is None:
            return None
        try:
            return Decimal(s.replace(",", ".").replace(" ", ""))
        except InvalidOperation:
            err_console.print(_("error.invalid_cli_value", name=name, val=s))
            sys.exit(1)

    # --- Stage 1: mandatory inputs ---
    pp = _parse_opt(property_price, "property-price")
    if pp is None:
        pp = _prompt_decimal(
            _("prompt.property_price"),
            positive=True,
            help_text=_("help.property_price"),
        )

    inc = _parse_opt(income, "income")
    if inc is None:
        saved_inc = preferences.saved_decimal(prefs, "monthly_net_income")
        if saved_inc is not None:
            inc = _prompt_decimal_with_default(_("prompt.income"), saved_inc, positive=True)
        else:
            inc = _prompt_decimal(_("prompt.income"), positive=True, help_text=_("help.income"))

    sav = _parse_opt(savings, "savings")
    if sav is None:
        saved_sav = preferences.saved_decimal(prefs, "available_savings")
        if saved_sav is not None:
            sav = _prompt_decimal_with_default(_("prompt.savings"), saved_sav, allow_zero=True, positive=False)
        else:
            sav = _prompt_decimal(_("prompt.savings"), allow_zero=True, positive=False, help_text=_("help.savings"))

    # --- Profile summary + two-stage gate ---
    country_code = (country or DEFAULT_COUNTRY).upper()
    _display_profile_summary(store, country_code)

    # If all optional inputs were already supplied via CLI flags, skip the interactive gate.
    all_optional_set = (purchase_taxes is not None and down_payment is not None and duration is not None)
    use_defaults = all_optional_set
    if not all_optional_set:
        try:
            gate_raw = console.input(f"[bold]{_('prompt.gate')}[/bold]").strip()
        except (EOFError, KeyboardInterrupt):
            gate_raw = "y"
        use_defaults = _is_yes(gate_raw)

    # --- Parse --duration (CLI flag) ---
    fixed_duration: int | None = None
    if duration is not None:
        raw_dur = duration.strip().lower()
        try:
            if raw_dur.endswith("y"):
                fixed_duration = int(raw_dur[:-1]) * 12
            else:
                fixed_duration = int(raw_dur)
        except ValueError:
            err_console.print(_("error.invalid_cli_duration", val=duration))
            sys.exit(1)
        if fixed_duration < 12:
            err_console.print(_("error.duration_too_short_cli"))
            sys.exit(1)

    # --- Stage 2: optional inputs (only asked in detailed mode) ---
    pt = _parse_opt(purchase_taxes, "purchase-taxes")
    preferred_dp: Decimal | None = _parse_opt(down_payment, "down-payment")
    opp_rate_decimal = _parse_opt(opp_rate, "opp-rate")

    if not use_defaults:
        # Purchase taxes with inline estimate hint
        if pt is None:
            tax_rate_est = Decimal(str(store.get_field(country_code, "purchase_tax_rate")))
            est_taxes = (pp * tax_rate_est).quantize(Decimal("0.01"), rounding=_ROUND_HALF_UP)
            cur_sym = str(store.get_field(country_code, "currency"))
            try:
                raw_pt = console.input(
                    f"[bold]{_('prompt.purchase_taxes', est=f'{est_taxes:,.0f}', cur=cur_sym)}[/bold] "
                ).strip()
            except (EOFError, KeyboardInterrupt):
                raw_pt = ""
            if raw_pt == "?":
                console.print(f"  [dim]{_('help.purchase_taxes')}[/dim]")
                raw_pt = ""
            if raw_pt:
                try:
                    pt = Decimal(raw_pt.replace(",", ".").replace(" ", ""))
                except InvalidOperation:
                    err_console.print(_("error.invalid_number", val=raw_pt))

        # Preferred down payment with savings ceiling as hint
        if preferred_dp is None:
            try:
                raw_dp = console.input(
                    f"[bold]{_('prompt.down_payment', max_dp=f'{sav:,.0f}')}[/bold] "
                ).strip()
            except (EOFError, KeyboardInterrupt):
                raw_dp = ""
            if raw_dp == "?":
                console.print(f"  [dim]{_('help.down_payment')}[/dim]")
                raw_dp = ""
            if raw_dp:
                try:
                    preferred_dp = Decimal(raw_dp.replace(",", ".").replace(" ", ""))
                except InvalidOperation:
                    err_console.print(_("error.invalid_number", val=raw_dp))

        # Loan duration
        if fixed_duration is None:
            try:
                raw_dur2 = console.input(
                    f"[bold]{_('prompt.duration', default_y=DEFAULT_LOAN_DURATION_MONTHS // 12, default_m=DEFAULT_LOAN_DURATION_MONTHS)}[/bold] "
                ).strip()
            except (EOFError, KeyboardInterrupt):
                raw_dur2 = ""
            if raw_dur2 == "?":
                console.print(f"  [dim]{_('help.duration', default_y=DEFAULT_LOAN_DURATION_MONTHS // 12)}[/dim]")
                raw_dur2 = ""
            if raw_dur2:
                raw_dur2 = raw_dur2.strip().lower()
                try:
                    if raw_dur2.endswith("y"):
                        fixed_duration = int(raw_dur2[:-1]) * 12
                    else:
                        fixed_duration = int(raw_dur2)
                    if fixed_duration < 12:
                        err_console.print(_("error.duration_too_short"))
                        fixed_duration = None
                except ValueError:
                    err_console.print(_("error.invalid_duration", val=raw_dur2))

        # Opportunity cost rate
        if opp_rate_decimal is None:
            default_opp_pct = f"{SWEET_SPOT_OPPORTUNITY_COST_RATE * 100:.1f}"
            try:
                raw_opp = console.input(
                    f"[bold]{_('prompt.opp_rate', default=default_opp_pct)}[/bold] "
                ).strip()
            except (EOFError, KeyboardInterrupt):
                raw_opp = ""
            if raw_opp == "?":
                console.print(f"  [dim]{_('help.opp_rate')}[/dim]")
                raw_opp = ""
            if raw_opp:
                try:
                    opp_rate_decimal = Decimal(raw_opp.replace(",", ".").replace(" ", ""))
                except InvalidOperation:
                    err_console.print(_("error.invalid_number", val=raw_opp))

    inputs = UserInputs(
        property_price=pp,
        monthly_net_income=inc,
        available_savings=sav,
        purchase_taxes=pt,
        country=country,
        profile_quality=quality,  # type: ignore[arg-type]
        optimization_preference=preference,
        preferred_down_payment=preferred_dp,
        fixed_loan_duration_months=fixed_duration,
        opportunity_cost_rate=opp_rate_decimal,
    )

    # Apply saved optional preferences (CLI flags and interactive entries take precedence
    # because they are already non-None on inputs; apply_to_inputs only sets None fields).
    _apply_saved_optionals(prefs, inputs)

    try:
        interactive_loop(inputs, store)
    except (KeyboardInterrupt, EOFError):
        preferences.save(inputs, store)
        console.print(_("action.session_ended"))
