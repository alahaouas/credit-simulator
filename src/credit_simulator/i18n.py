"""Internationalisation: locale management and translation lookup.

Supported locales: 'en' (default), 'fr'.
Auto-detection order:
  1. CREDIT_SIMULATOR_LOCALE env var
  2. LANG env var
  3. System locale (locale.getlocale)
  4. Fallback: 'en'

Usage:
    from .i18n import _, set_locale, detect_locale
    set_locale(detect_locale())
    print(_("prompt.property_price"))
    print(_("reason.efficient", yield_pct="3.45", opp_pct="3.50", n=6))
"""
from __future__ import annotations

import locale as _sys_locale
import os

# ── Translation registry ──────────────────────────────────────────────────────

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # === CLI prompts ===
        "prompt.property_price": "Property price?",
        "prompt.income": "Monthly net income?",
        "prompt.savings": "Available savings?",
        "prompt.purchase_taxes": "Purchase taxes? [Enter for ~{est} {cur}, ? for help]",
        "prompt.down_payment": "Preferred down payment? [max {max_dp}, Enter to optimise, ? for help]",
        "prompt.duration": "Loan duration? [Enter for {default_y}y ({default_m} months), ? for help]",
        "prompt.opp_rate": "Opportunity cost rate? [Enter for {default}%, ? for help]",
        "prompt.country": "Country code ({countries}): ",
        "prompt.quality": "Profile quality (average / best): ",
        "prompt.preference": "Optimization preference: ",
        "prompt.field_to_update": "Field to update: ",
        "prompt.field_to_reset": "Field to reset to profile default: ",
        "prompt.update_mode": "Update mode (manual / online): ",
        "prompt.gate": "Use all country defaults and run immediately? [Y/n]: ",
        "prompt.fallback_manual": "Fall back to manual entry? (y/n): ",
        "prompt.replace_override": "Replace current override? (y/n): ",
        "prompt.taxes_financeable": "Taxes financeable? (true / false): ",
        "prompt.new_rate": "New annual rate (e.g. 0.035 for 3.5%): ",
        "prompt.new_insurance": "New insurance rate (e.g. 0.003 for 0.3%): ",
        "prompt.new_tax": "New purchase tax rate (e.g. 0.075 for 7.5%): ",
        "prompt.new_min_dp": "New min down payment ratio (e.g. 0.20 for 20%): ",
        "prompt.new_max_debt": "New max debt ratio (e.g. 0.35 for 35%): ",
        "prompt.new_max_dur": "New max loan duration (months, 12–600): ",
        "prompt.new_property_price": "New property price: ",
        "prompt.new_taxes": "New purchase taxes: ",
        "prompt.new_rate_direct": "New annual interest rate (e.g. 0.035): ",
        "prompt.new_insurance_direct": "New insurance rate (e.g. 0.003): ",
        "prompt.new_min_dp_direct": "New min down payment ratio (e.g. 0.20): ",
        "prompt.new_max_dur_direct": "Fixed loan duration (months, e.g. 240 for 20y): ",
        "prompt.new_income": "New monthly net income: ",
        "prompt.new_savings": "New available savings (maximum you can use for down payment): ",
        "prompt.new_preferred_dp": "New preferred down payment: ",
        "prompt.new_max_debt_direct": "New max debt ratio (e.g. 0.35 for 35%): ",
        "prompt.new_max_payment": "New max monthly payment: ",
        "prompt.new_opp_rate": "New opportunity cost rate (e.g. 0.04 for 4%): ",

        # === Help texts ===
        "help.property_price": "The market value of the property (before taxes and fees).",
        "help.income": "Your total take-home pay per month. Used to check the debt-to-income ratio.",
        "help.savings": (
            "The maximum amount you can draw on for the down payment. "
            "The optimizer will never exceed this ceiling."
        ),
        "help.purchase_taxes": (
            "Total notary fees, registration taxes, and agency fees. "
            "Leave blank to estimate from the country profile."
        ),
        "help.down_payment": (
            "Pin the optimizer to a specific down payment amount. "
            "Leave blank to let the optimizer find the best amount."
        ),
        "help.duration": "Loan duration in months (e.g. 240) or years (e.g. 20y). Default: {default_y} years.",
        "help.opp_rate": (
            "Annual return you expect to earn if you invest the surplus savings "
            "instead of putting them into the down payment. "
            "Use your savings account rate, ETF expected return, etc."
        ),

        # === Actions ===
        "action.menu": (
            "[bold]Actions:[/bold] "
            "[cyan]update[/cyan] · [cyan]reset[/cyan] · [cyan]profile[/cyan] · "
            "[cyan]schedule[/cyan] · [cyan]sweetspot[/cyan] · [cyan]params[/cyan] · [cyan]exit[/cyan]"
        ),
        "action.goodbye": "Goodbye.",
        "action.update_cancelled": "\n  Update cancelled.",
        "action.keeping_current": "  Keeping current value.",
        "action.session_ended": "\nSession ended.",
        "action.preferences_list": "  Preferences: {prefs}",
        "action.fields_list": "  Fields: {fields}",
        "action.profile_fields": (
            "  Fields: annual_rate, insurance_rate, purchase_tax_rate, "
            "taxes_financeable, min_down_payment_ratio, max_debt_ratio, max_loan_duration_months"
        ),

        # === Status messages ===
        "status.resolving": "  [cyan]Resolving simulation parameters...[/cyan]",
        "status.generating_schedule": "  [cyan]Generating amortization schedule...[/cyan]",
        "status.optimizing": "  [cyan]Optimizing loan plan...[/cyan]",
        "status.sweet_spot": "  [cyan]Analyzing sweet spot...[/cyan]",
        "status.fetching_rate": "  Fetching latest average annual rate for {country}…",

        # === Error messages ===
        "error.no_result": "No simulation result available yet.",
        "error.run_first": "Run a simulation first.",
        "error.fetch_failed": "  Fetch failed: {exc}",
        "error.sweet_spot_failed": "Sweet-spot analysis failed: {exc}",
        "error.param_error": "Parameter error: {exc}",
        "error.unknown_action": "  Unknown action '{action}'.",
        "error.unknown_field": "  Unknown field '{field}'.",
        "error.unknown_preference": "  Unknown preference '{pref}'.",
        "error.unsupported_country": "  Unsupported country '{country}'.",
        "error.invalid_number": "  Invalid number: '{val}'. Type ? for help.",
        "error.invalid_integer": "  Invalid integer: '{val}'. Type ? for help.",
        "error.must_be_positive": "  Value must be > 0.",
        "error.must_be_nonneg": "  Value must be >= 0.",
        "error.must_be_at_least": "  Value must be >= {min_val}.",
        "error.enter_average_best": "  Enter 'average' or 'best'.",
        "error.enter_manual_online": "  Enter 'manual' or 'online'.",
        "error.enter_true_false": "  Enter 'true' or 'false'.",
        "error.max_duration_exceeded": "  Max duration cannot exceed 600 months.",
        "error.duration_too_short": "  Duration must be at least 12 months. Using default.",
        "error.invalid_duration": "  Invalid duration '{val}'. Using default.",
        "error.invalid_cli_value": "Invalid value for --{name}: '{val}'",
        "error.invalid_cli_duration": (
            "Invalid --duration value '{val}'. Use months (e.g. 240) or years (e.g. 20y)."
        ),
        "error.duration_too_short_cli": "--duration must be at least 12 months.",
        "error.no_help": "No additional help available.",

        # === InfeasibleError messages ===
        "error.infeasible.savings": (
            "Insufficient savings: you need at least {min_dp} {currency} as a down payment "
            "(you have {savings} {currency})."
        ),
        "error.infeasible.preferred_below_min": (
            "Preferred down payment {preferred} {currency} "
            "is below the required minimum of {min_dp} {currency}."
        ),
        "error.infeasible.preferred_above_savings": (
            "Preferred down payment {preferred} {currency} "
            "exceeds available savings of {savings} {currency}."
        ),
        "error.infeasible.payment_too_high": (
            "Monthly payment for the minimum loan "
            "({principal} {currency} over {months} months) "
            "would be {payment} {currency}, "
            "exceeding the effective monthly cap of {cap} {currency} "
            "(DTI limit: {dti_pct} of income, "
            "absolute cap: {abs_cap} {currency})."
        ),

        # === Panels ===
        "panel.credit_simulator": "[bold blue]Credit Simulator[/bold blue]",
        "panel.optimal_plan": (
            "[bold green]Optimal Loan Plan[/bold green] — "
            "{country} / {quality} / preference: {preference}"
        ),
        "panel.country_defaults": "Country Defaults",
        "panel.ineligible": "[bold red]Ineligible[/bold red]\n{exc}",
        "panel.no_plan": "[bold red]No feasible plan found[/bold red]\n{exc}",

        # === Result table labels ===
        "label.down_payment": "Down payment",
        "label.loan_principal": "Loan principal",
        "label.loan_duration": "Loan duration",
        "label.monthly_installment": "Monthly installment",
        "label.emi": "  └ EMI (P+I)",
        "label.insurance": "  └ Insurance",
        "label.first_month_interest": "First month interest",
        "label.apr": "APR (effective annual rate)",
        "label.total_interest": "Total interest paid",
        "label.total_insurance": "Total insurance paid",
        "label.total_cost": "Total cost of credit",
        "label.total_repaid": "Total repaid",
        "label.dti": "Debt ratio (DTI)",
        "label.ltv": "LTV ratio",

        # === Params table ===
        "table.current_params": "Current Parameters",
        "table.col.parameter": "Parameter",
        "table.col.value": "Value",
        "table.col.source": "Source",

        # === Amortization schedule ===
        "table.amortization": "Amortization Schedule",
        "col.period": "Period",
        "col.opening_bal": "Opening Bal.",
        "col.installment": "Installment",
        "col.principal": "Principal",
        "col.interest": "Interest",
        "col.insurance": "Insurance",
        "col.closing_bal": "Closing Bal.",

        # === Profile summary ===
        "profile.yes": "[green]yes[/green]",
        "profile.no": "[yellow]no[/yellow]",
        "profile.updated": "  [green]Updated {country} {quality} {field} to {value}[/green]",
        "profile.fetched_applied": "  [green]Applied fetched rate: {rate} for {country} {quality}[/green]",
        "profile.fetched_shown": "  Fetched rate: [bold]{fetched}[/bold]  (current override: {current})",
        "profile.summary": (
            "[bold]{country}[/bold] profile  (currency: {currency})\n"
            "  Interest  avg [cyan]{avg_rate}[/cyan]  /  best [cyan]{best_rate}[/cyan]\n"
            "  Insurance avg [cyan]{avg_ins}[/cyan]  /  best [cyan]{best_ins}[/cyan]\n"
            "  Purchase taxes ~[cyan]{tax_rate}[/cyan] of price  ·  financeable: {financed}\n"
            "  Min down pmt [cyan]{min_dp}[/cyan]  ·  "
            "Max DTI [cyan]{max_dti}[/cyan]  ·  Max duration [cyan]{max_dur}y[/cyan]"
        ),

        # === Sweet-spot panel ===
        "panel.sweet_spot": (
            "[bold yellow]Down Payment Sweet-Spot Analysis[/bold yellow] "
            "— {duration} — all amounts in {currency}"
        ),
        "sweetspot.marginal_saving": (
            "  Marginal saving per extra 1 000 {currency} of down payment: "
            "[bold]{saving} {currency}[/bold] in total cost over the loan term"
        ),
        "sweetspot.yield_line": (
            "  Effective yield (loan APR):  [bold]{yield_pct}[/bold]   "
            "Reference rate (opportunity cost): [bold]{opp_pct}[/bold]   {verdict}"
        ),
        "sweetspot.crossover_dim": "  [dim]{note}[/dim]",
        "sweetspot.verdict.efficient": "[green]EFFICIENT — mortgage beats the market[/green]",
        "sweetspot.verdict.inefficient": "[yellow]INEFFICIENT — market beats the mortgage[/yellow]",
        "sweetspot.col.milestone": "Milestone",
        "sweetspot.col.down_pmt": "Down pmt",
        "sweetspot.col.rate": "Rate",
        "sweetspot.col.monthly": "Monthly",
        "sweetspot.col.dti": "DTI",
        "sweetspot.col.ltv": "LTV",
        "sweetspot.col.total_cost": "Total cost",
        "sweetspot.col.liquidity": "Liquidity",
        "sweetspot.verdict_line": "[bold]Verdict:[/bold] {reason}",
        "sweetspot.tier_header": (
            "[bold]Per-tier down-payment economics[/bold] "
            "(extra 1 000 {currency} in each LTV band):"
        ),
        "sweetspot.col.ltv_tier": "LTV tier",
        "sweetspot.col.delta": "Delta",
        "sweetspot.col.saves": "Saves (total)",
        "sweetspot.col.yield": "Yield",
        "sweetspot.tier_footnote": (
            "  [dim magenta]Magenta row = rate floor: paying beyond this LTV tier "
            "reduces principal but not the interest rate.[/dim magenta]"
        ),

        # === Milestone labels ===
        "milestone.minimum": "Minimum",
        "milestone.maximum": "Maximum",
        "milestone.sweet_spot": "★  Sweet spot",
        "milestone.sweet_spot_rate_floor": "★  Sweet spot (rate floor)",
        "milestone.rate_floor": "Rate floor ─ no gain beyond",
        "milestone.ltv_ref": "LTV {pct}% (ref)",
        "milestone.ltv_rate_cross": "LTV≤{pct}% rate↓",
        "milestone.reserve_cap": "{n}m reserve cap",
        "milestone.your_choice": "Your choice",
        "milestone.your_choice_suffix": "  ← Your choice",

        # === Tier delta labels ===
        "tier.base": "base",
        "tier.surcharge": "+{pct}%",
        "tier.discount": "−{pct}%",

        # === Sweet-spot reason strings ===
        "reason.efficient": (
            "Loan APR ({yield_pct}%) exceeds the reference rate ({opp_pct}%): "
            "paying down the mortgage gives a better return than investing the "
            "surplus. Maximise the down payment up to the {n}-month income "
            "reserve ceiling — do not go further."
        ),
        "reason.efficient_capped_at_rate_floor": (
            "Loan APR at the effective floor ({yield_pct}%) exceeds the reference rate ({opp_pct}%): "
            "paying down the mortgage is efficient up to the rate floor. "
            "Beyond it the best-tier APR drops to {rf_yield_pct}%, which is at or below the "
            "reference rate ({opp_pct}%) — stop here and invest any further surplus."
        ),
        "reason.inefficient_exits_surcharge": (
            "Loan APR ({yield_pct}%) is at or below the reference rate ({opp_pct}%): "
            "investing the surplus could earn more than the mortgage interest saved. "
            "However, the minimum down payment ({min_dp} {currency}) "
            "falls in an LTV surcharge tier — committing an extra "
            "{extra} {currency} immediately exits the penalty zone "
            "and is almost always worth it regardless of opportunity cost. "
            "Beyond this floor, invest any further surplus."
        ),
        "reason.inefficient_minimum": (
            "Loan APR ({yield_pct}%) is at or below the reference rate ({opp_pct}%): "
            "investing the surplus earns more than it saves in mortgage interest. "
            "Put only the minimum required down payment; every extra euro costs "
            "you ({opp_pct}% − {yield_pct}%) in forgone returns."
        ),
        "reserve_warning": (
            "Note: even the minimum down payment exceeds the {n}-month income reserve "
            "({reserve} {currency}). "
            "Ensure you have sufficient emergency funds before proceeding."
        ),
        "crossover_note": (
            "Crossover rate: {yield_pct}% (loan APR). "
            "If your expected investment return exceeds this, invest the surplus; "
            "below it, paying down the mortgage gives a better risk-free return."
        ),
    },

    # ── French ────────────────────────────────────────────────────────────────

    "fr": {
        # === CLI prompts ===
        "prompt.property_price": "Prix du bien ?",
        "prompt.income": "Revenu net mensuel ?",
        "prompt.savings": "Épargne disponible ?",
        "prompt.purchase_taxes": "Frais d'acquisition ? [Entrée pour ~{est} {cur}, ? pour aide]",
        "prompt.down_payment": "Apport souhaité ? [max {max_dp}, Entrée pour optimiser, ? pour aide]",
        "prompt.duration": "Durée du prêt ? [Entrée pour {default_y} ans ({default_m} mois), ? pour aide]",
        "prompt.opp_rate": "Taux d'opportunité ? [Entrée pour {default}%, ? pour aide]",
        "prompt.country": "Code pays ({countries}) : ",
        "prompt.quality": "Qualité du profil (average / best) : ",
        "prompt.preference": "Préférence d'optimisation : ",
        "prompt.field_to_update": "Champ à modifier : ",
        "prompt.field_to_reset": "Champ à réinitialiser au défaut du profil : ",
        "prompt.update_mode": "Mode de mise à jour (manual / online) : ",
        "prompt.gate": "Utiliser les paramètres par défaut du pays et lancer immédiatement ? [O/n] : ",
        "prompt.fallback_manual": "Saisie manuelle en secours ? (o/n) : ",
        "prompt.replace_override": "Remplacer la valeur actuelle ? (o/n) : ",
        "prompt.taxes_financeable": "Frais finançables ? (true / false) : ",
        "prompt.new_rate": "Nouveau taux annuel (ex. 0.035 pour 3,5 %) : ",
        "prompt.new_insurance": "Nouveau taux d'assurance (ex. 0.003 pour 0,3 %) : ",
        "prompt.new_tax": "Nouveau taux de frais (ex. 0.075 pour 7,5 %) : ",
        "prompt.new_min_dp": "Nouveau apport minimum (ex. 0.20 pour 20 %) : ",
        "prompt.new_max_debt": "Nouveau taux d'endettement max (ex. 0.35 pour 35 %) : ",
        "prompt.new_max_dur": "Nouvelle durée max (mois, 12–600) : ",
        "prompt.new_property_price": "Nouveau prix du bien : ",
        "prompt.new_taxes": "Nouveaux frais d'acquisition : ",
        "prompt.new_rate_direct": "Nouveau taux d'intérêt annuel (ex. 0.035) : ",
        "prompt.new_insurance_direct": "Nouveau taux d'assurance (ex. 0.003) : ",
        "prompt.new_min_dp_direct": "Nouveau apport minimum (ex. 0.20) : ",
        "prompt.new_max_dur_direct": "Durée fixe du prêt (mois, ex. 240 pour 20 ans) : ",
        "prompt.new_income": "Nouveau revenu net mensuel : ",
        "prompt.new_savings": "Nouvelle épargne disponible (maximum mobilisable pour l'apport) : ",
        "prompt.new_preferred_dp": "Nouvel apport souhaité : ",
        "prompt.new_max_debt_direct": "Nouveau taux d'endettement max (ex. 0.35 pour 35 %) : ",
        "prompt.new_max_payment": "Nouvelle mensualité maximum : ",
        "prompt.new_opp_rate": "Nouveau taux d'opportunité (ex. 0.04 pour 4 %) : ",

        # === Help texts ===
        "help.property_price": "Valeur vénale du bien (hors frais et taxes).",
        "help.income": "Votre salaire net mensuel total. Utilisé pour vérifier le taux d'endettement.",
        "help.savings": (
            "Le montant maximum que vous pouvez mobiliser pour l'apport. "
            "L'optimiseur ne dépassera jamais ce plafond."
        ),
        "help.purchase_taxes": (
            "Frais de notaire, droits d'enregistrement et frais d'agence. "
            "Laisser vide pour estimer d'après le profil pays."
        ),
        "help.down_payment": (
            "Fixer l'optimiseur sur un montant d'apport précis. "
            "Laisser vide pour laisser l'optimiseur choisir."
        ),
        "help.duration": "Durée en mois (ex. 240) ou en années (ex. 20y). Défaut : {default_y} ans.",
        "help.opp_rate": (
            "Rendement annuel attendu si vous investissez l'épargne excédentaire "
            "plutôt que de l'apporter. Utilisez votre taux d'épargne, rendement ETF, etc."
        ),

        # === Actions ===
        "action.menu": (
            "[bold]Actions :[/bold] "
            "[cyan]update[/cyan] · [cyan]reset[/cyan] · [cyan]profile[/cyan] · "
            "[cyan]schedule[/cyan] · [cyan]sweetspot[/cyan] · [cyan]params[/cyan] · [cyan]exit[/cyan]"
        ),
        "action.goodbye": "Au revoir.",
        "action.update_cancelled": "\n  Mise à jour annulée.",
        "action.keeping_current": "  Valeur conservée.",
        "action.session_ended": "\nSession terminée.",
        "action.preferences_list": "  Préférences : {prefs}",
        "action.fields_list": "  Champs : {fields}",
        "action.profile_fields": (
            "  Champs : annual_rate, insurance_rate, purchase_tax_rate, "
            "taxes_financeable, min_down_payment_ratio, max_debt_ratio, max_loan_duration_months"
        ),

        # === Status messages ===
        "status.resolving": "  [cyan]Résolution des paramètres de simulation...[/cyan]",
        "status.generating_schedule": "  [cyan]Génération du tableau d'amortissement...[/cyan]",
        "status.optimizing": "  [cyan]Optimisation du plan de prêt...[/cyan]",
        "status.sweet_spot": "  [cyan]Analyse de l'apport optimal...[/cyan]",
        "status.fetching_rate": "  Récupération du taux moyen pour {country}…",

        # === Error messages ===
        "error.no_result": "Aucun résultat de simulation disponible.",
        "error.run_first": "Lancez d'abord une simulation.",
        "error.fetch_failed": "  Récupération échouée : {exc}",
        "error.sweet_spot_failed": "Analyse du point optimal échouée : {exc}",
        "error.param_error": "Erreur de paramètre : {exc}",
        "error.unknown_action": "  Action inconnue « {action} ».",
        "error.unknown_field": "  Champ inconnu « {field} ».",
        "error.unknown_preference": "  Préférence inconnue « {pref} ».",
        "error.unsupported_country": "  Pays non pris en charge « {country} ».",
        "error.invalid_number": "  Nombre invalide : « {val} ». Tapez ? pour l'aide.",
        "error.invalid_integer": "  Entier invalide : « {val} ». Tapez ? pour l'aide.",
        "error.must_be_positive": "  La valeur doit être > 0.",
        "error.must_be_nonneg": "  La valeur doit être >= 0.",
        "error.must_be_at_least": "  La valeur doit être >= {min_val}.",
        "error.enter_average_best": "  Saisissez « average » ou « best ».",
        "error.enter_manual_online": "  Saisissez « manual » ou « online ».",
        "error.enter_true_false": "  Saisissez « true » ou « false ».",
        "error.max_duration_exceeded": "  La durée max ne peut pas dépasser 600 mois.",
        "error.duration_too_short": "  La durée doit être d'au moins 12 mois. Valeur par défaut appliquée.",
        "error.invalid_duration": "  Durée invalide « {val} ». Valeur par défaut appliquée.",
        "error.invalid_cli_value": "Valeur invalide pour --{name} : « {val} »",
        "error.invalid_cli_duration": (
            "Valeur --duration invalide « {val} ». "
            "Utilisez des mois (ex. 240) ou des années (ex. 20y)."
        ),
        "error.duration_too_short_cli": "--duration doit être d'au moins 12 mois.",
        "error.no_help": "Aucune aide supplémentaire disponible.",

        # === InfeasibleError messages ===
        "error.infeasible.savings": (
            "Épargne insuffisante : il vous faut au moins {min_dp} {currency} d'apport "
            "(vous disposez de {savings} {currency})."
        ),
        "error.infeasible.preferred_below_min": (
            "L'apport souhaité {preferred} {currency} "
            "est inférieur au minimum requis de {min_dp} {currency}."
        ),
        "error.infeasible.preferred_above_savings": (
            "L'apport souhaité {preferred} {currency} "
            "dépasse l'épargne disponible de {savings} {currency}."
        ),
        "error.infeasible.payment_too_high": (
            "La mensualité pour le prêt minimum "
            "({principal} {currency} sur {months} mois) "
            "serait de {payment} {currency}, "
            "dépassant le plafond mensuel effectif de {cap} {currency} "
            "(taux d'endettement max : {dti_pct} du revenu, "
            "plafond absolu : {abs_cap} {currency})."
        ),

        # === Panels ===
        "panel.credit_simulator": "[bold blue]Simulateur de crédit[/bold blue]",
        "panel.optimal_plan": (
            "[bold green]Plan de prêt optimal[/bold green] — "
            "{country} / {quality} / préférence : {preference}"
        ),
        "panel.country_defaults": "Paramètres pays",
        "panel.ineligible": "[bold red]Non éligible[/bold red]\n{exc}",
        "panel.no_plan": "[bold red]Aucun plan réalisable trouvé[/bold red]\n{exc}",

        # === Result table labels ===
        "label.down_payment": "Apport initial",
        "label.loan_principal": "Capital emprunté",
        "label.loan_duration": "Durée du prêt",
        "label.monthly_installment": "Mensualité totale",
        "label.emi": "  └ Échéance (K+I)",
        "label.insurance": "  └ Assurance",
        "label.first_month_interest": "Intérêts 1er mois",
        "label.apr": "TAEG (taux effectif annuel)",
        "label.total_interest": "Total des intérêts payés",
        "label.total_insurance": "Total des assurances",
        "label.total_cost": "Coût total du crédit",
        "label.total_repaid": "Montant total remboursé",
        "label.dti": "Taux d'endettement (DTI)",
        "label.ltv": "Quotité de financement (LTV)",

        # === Params table ===
        "table.current_params": "Paramètres actuels",
        "table.col.parameter": "Paramètre",
        "table.col.value": "Valeur",
        "table.col.source": "Source",

        # === Amortization schedule ===
        "table.amortization": "Tableau d'amortissement",
        "col.period": "Période",
        "col.opening_bal": "Capital début",
        "col.installment": "Mensualité",
        "col.principal": "Capital",
        "col.interest": "Intérêts",
        "col.insurance": "Assurance",
        "col.closing_bal": "Capital fin",

        # === Profile summary ===
        "profile.yes": "[green]oui[/green]",
        "profile.no": "[yellow]non[/yellow]",
        "profile.updated": "  [green]Mis à jour {country} {quality} {field} → {value}[/green]",
        "profile.fetched_applied": "  [green]Taux récupéré appliqué : {rate} pour {country} {quality}[/green]",
        "profile.fetched_shown": "  Taux récupéré : [bold]{fetched}[/bold]  (valeur actuelle : {current})",
        "profile.summary": (
            "Profil [bold]{country}[/bold]  (devise : {currency})\n"
            "  Taux  moy [cyan]{avg_rate}[/cyan]  /  meilleur [cyan]{best_rate}[/cyan]\n"
            "  Assurance moy [cyan]{avg_ins}[/cyan]  /  meilleure [cyan]{best_ins}[/cyan]\n"
            "  Frais d'acq. ~[cyan]{tax_rate}[/cyan] du prix  ·  finançables : {financed}\n"
            "  Apport min [cyan]{min_dp}[/cyan]  ·  "
            "DTI max [cyan]{max_dti}[/cyan]  ·  Durée max [cyan]{max_dur} ans[/cyan]"
        ),

        # === Sweet-spot panel ===
        "panel.sweet_spot": (
            "[bold yellow]Analyse de l'apport optimal[/bold yellow] "
            "— {duration} — montants en {currency}"
        ),
        "sweetspot.marginal_saving": (
            "  Économie marginale par tranche de 1 000 {currency} d'apport : "
            "[bold]{saving} {currency}[/bold] sur le coût total du crédit"
        ),
        "sweetspot.yield_line": (
            "  Rendement effectif (TAEG) :  [bold]{yield_pct}[/bold]   "
            "Taux de référence (opportunité) : [bold]{opp_pct}[/bold]   {verdict}"
        ),
        "sweetspot.crossover_dim": "  [dim]{note}[/dim]",
        "sweetspot.verdict.efficient": "[green]EFFICACE — le remboursement bat le marché[/green]",
        "sweetspot.verdict.inefficient": "[yellow]INEFFICACE — le marché bat le remboursement[/yellow]",
        "sweetspot.col.milestone": "Jalon",
        "sweetspot.col.down_pmt": "Apport",
        "sweetspot.col.rate": "Taux",
        "sweetspot.col.monthly": "Mensuel",
        "sweetspot.col.dti": "DTI",
        "sweetspot.col.ltv": "LTV",
        "sweetspot.col.total_cost": "Coût total",
        "sweetspot.col.liquidity": "Liquidité",
        "sweetspot.verdict_line": "[bold]Verdict :[/bold] {reason}",
        "sweetspot.tier_header": (
            "[bold]Économie par palier de LTV[/bold] "
            "(tranche de 1 000 {currency}) :"
        ),
        "sweetspot.col.ltv_tier": "Palier LTV",
        "sweetspot.col.delta": "Delta",
        "sweetspot.col.saves": "Économie (total)",
        "sweetspot.col.yield": "Rendement",
        "sweetspot.tier_footnote": (
            "  [dim magenta]Ligne magenta = plancher de taux : au-delà, "
            "l'apport réduit le capital mais pas le taux.[/dim magenta]"
        ),

        # === Milestone labels ===
        "milestone.minimum": "Minimum",
        "milestone.maximum": "Maximum",
        "milestone.sweet_spot": "★  Point optimal",
        "milestone.sweet_spot_rate_floor": "★  Point optimal (plancher)",
        "milestone.rate_floor": "Plancher de taux — aucun gain au-delà",
        "milestone.ltv_ref": "LTV {pct}% (réf.)",
        "milestone.ltv_rate_cross": "LTV≤{pct}% taux↓",
        "milestone.reserve_cap": "Plafond réserve {n}m",
        "milestone.your_choice": "Votre choix",
        "milestone.your_choice_suffix": "  ← Votre choix",

        # === Tier delta labels ===
        "tier.base": "base",
        "tier.surcharge": "+{pct}%",
        "tier.discount": "−{pct}%",

        # === Sweet-spot reason strings ===
        "reason.efficient": (
            "Le TAEG du prêt ({yield_pct}%) dépasse le taux de référence ({opp_pct}%) : "
            "rembourser davantage est plus rentable qu'investir le surplus. "
            "Maximisez l'apport jusqu'au plafond de réserve de {n} mois de revenus — "
            "ne dépassez pas ce seuil."
        ),
        "reason.efficient_capped_at_rate_floor": (
            "Le TAEG au plancher effectif ({yield_pct}%) dépasse le taux de référence ({opp_pct}%) : "
            "rembourser est rentable jusqu'au plancher de taux. "
            "Au-delà, le TAEG du meilleur palier tombe à {rf_yield_pct}%, "
            "en dessous du taux de référence ({opp_pct}%) "
            "— arrêtez-vous ici et investissez le reste."
        ),
        "reason.inefficient_exits_surcharge": (
            "Le TAEG ({yield_pct}%) est inférieur ou égal au taux de référence ({opp_pct}%) : "
            "investir le surplus serait plus rentable. "
            "Cependant, l'apport minimum ({min_dp} {currency}) se situe dans une tranche majorée "
            "— engager {extra} {currency} supplémentaires sort immédiatement de la zone pénalisée "
            "et vaut presque toujours le coût. Au-delà, investissez le reste."
        ),
        "reason.inefficient_minimum": (
            "Le TAEG ({yield_pct}%) est inférieur ou égal au taux de référence ({opp_pct}%) : "
            "investir le surplus rapporte plus qu'il n'économise en intérêts. "
            "N'apportez que le minimum requis ; chaque euro supplémentaire vous coûte "
            "({opp_pct}% − {yield_pct}%) en rendement non perçu."
        ),
        "reserve_warning": (
            "Note : même l'apport minimum dépasse la réserve de {n} mois de revenus "
            "({reserve} {currency}). "
            "Assurez-vous d'avoir suffisamment de fonds d'urgence avant de continuer."
        ),
        "crossover_note": (
            "Taux de croisement : {yield_pct}% (TAEG du prêt). "
            "Si votre rendement d'investissement dépasse ce seuil, investissez le surplus ; "
            "en dessous, rembourser le prêt offre un meilleur rendement sans risque."
        ),
    },
}

SUPPORTED_LOCALES: frozenset[str] = frozenset(TRANSLATIONS.keys())

# Active locale — module-level state, set once at startup
_current_locale: str = "en"


def set_locale(loc: str) -> None:
    """Set the active locale (silently ignores unsupported values)."""
    global _current_locale
    normalized = loc.lower().split("_")[0].split("-")[0]
    if normalized in TRANSLATIONS:
        _current_locale = normalized


def get_locale() -> str:
    return _current_locale


def _(key: str, **kwargs: object) -> str:
    """Return the translated string for *key* in the current locale.

    Falls back to 'en' if the key is missing in the active locale.
    Falls back to the bare key string if missing in 'en' too.
    Substitutes *kwargs* via str.format if provided.
    """
    text = TRANSLATIONS.get(_current_locale, {}).get(key)
    if text is None:
        text = TRANSLATIONS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text


def detect_locale() -> str:
    """Infer locale from environment without raising."""
    # 1. App-specific override
    env = os.environ.get("CREDIT_SIMULATOR_LOCALE", "")
    if env:
        normalized = env.lower().split("_")[0].split("-")[0]
        if normalized in TRANSLATIONS:
            return normalized

    # 2. LANG env var (Linux / macOS; sometimes set on Windows too)
    lang = os.environ.get("LANG", "").lower()
    for code in TRANSLATIONS:
        if lang.startswith(code):
            return code

    # 3. System locale
    try:
        sys_loc = _sys_locale.getlocale()[0] or ""
        normalized = sys_loc.lower().split("_")[0].split("-")[0]
        if normalized in TRANSLATIONS:
            return normalized
    except Exception:
        pass

    return "en"
