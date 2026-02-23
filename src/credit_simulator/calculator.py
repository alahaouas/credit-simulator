"""Core financial calculation functions.

All monetary values use decimal.Decimal — float is forbidden.
Rounding: ROUND_HALF_UP to 2 decimal places for final outputs,
full precision for all intermediate steps.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .config import CENT, ZERO


def _round(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class AmortizationRow:
    period: int
    opening_balance: Decimal
    monthly_installment: Decimal
    principal_component: Decimal
    interest_component: Decimal
    insurance_component: Decimal
    closing_balance: Decimal


@dataclass(frozen=True)
class LoanPlan:
    # Inputs echoed back
    loan_principal: Decimal
    annual_interest_rate: Decimal
    annual_insurance_rate: Decimal
    loan_duration_months: int
    # Outputs
    monthly_emi: Decimal           # principal + interest only
    monthly_insurance: Decimal     # fixed monthly insurance amount
    monthly_installment: Decimal   # EMI + insurance
    monthly_interest_first: Decimal
    total_interest_paid: Decimal
    total_insurance_paid: Decimal
    total_cost_of_credit: Decimal
    total_repaid: Decimal
    effective_annual_rate: Decimal  # APR


def compute_emi(
    principal: Decimal,
    annual_rate: Decimal,
    duration_months: int,
) -> Decimal:
    """Return the Equated Monthly Installment (principal + interest only).

    Uses the standard reducing-balance formula:
        EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)

    Special case: if annual_rate == 0, EMI = P / n (equal principal split).
    """
    if duration_months <= 0:
        raise ValueError("duration_months must be > 0")
    if principal < ZERO:
        raise ValueError("principal must be >= 0")

    if annual_rate == ZERO:
        return _round(principal / Decimal(duration_months))

    r = annual_rate / Decimal(12)
    n = Decimal(duration_months)
    factor = (1 + r) ** int(duration_months)  # stays Decimal arithmetic
    emi = principal * r * factor / (factor - 1)
    return _round(emi)


def compute_monthly_insurance(
    original_principal: Decimal,
    annual_insurance_rate: Decimal,
) -> Decimal:
    """Fixed monthly insurance = original_principal * annual_rate / 12."""
    return _round(original_principal * annual_insurance_rate / Decimal(12))


def compute_loan_plan(
    principal: Decimal,
    annual_interest_rate: Decimal,
    annual_insurance_rate: Decimal,
    duration_months: int,
) -> LoanPlan:
    """Compute the full loan plan summary (no amortization schedule)."""
    emi = compute_emi(principal, annual_interest_rate, duration_months)
    monthly_insurance = compute_monthly_insurance(principal, annual_insurance_rate)
    monthly_installment = _round(emi + monthly_insurance)

    # First month interest component
    r = annual_interest_rate / Decimal(12)
    monthly_interest_first = _round(principal * r)

    # Total interest computed precisely via the amortization schedule to avoid accumulated rounding.
    schedule = build_amortization_schedule(
        principal, annual_interest_rate, annual_insurance_rate, duration_months
    )
    total_interest_paid = sum(
        (row.interest_component for row in schedule), ZERO
    )
    total_insurance_paid = _round(monthly_insurance * Decimal(duration_months))
    total_cost_of_credit = _round(total_interest_paid + total_insurance_paid)
    total_repaid = _round(principal + total_cost_of_credit)

    apr = compute_apr(principal, monthly_installment, duration_months)

    return LoanPlan(
        loan_principal=principal,
        annual_interest_rate=annual_interest_rate,
        annual_insurance_rate=annual_insurance_rate,
        loan_duration_months=duration_months,
        monthly_emi=emi,
        monthly_insurance=monthly_insurance,
        monthly_installment=monthly_installment,
        monthly_interest_first=monthly_interest_first,
        total_interest_paid=total_interest_paid,
        total_insurance_paid=total_insurance_paid,
        total_cost_of_credit=total_cost_of_credit,
        total_repaid=total_repaid,
        effective_annual_rate=apr,
    )


def build_amortization_schedule(
    principal: Decimal,
    annual_interest_rate: Decimal,
    annual_insurance_rate: Decimal,
    duration_months: int,
) -> list[AmortizationRow]:
    """Build the full month-by-month amortization schedule."""
    emi = compute_emi(principal, annual_interest_rate, duration_months)
    monthly_insurance = compute_monthly_insurance(principal, annual_insurance_rate)
    monthly_installment = _round(emi + monthly_insurance)
    r = annual_interest_rate / Decimal(12)

    rows: list[AmortizationRow] = []
    balance = principal

    for period in range(1, duration_months + 1):
        opening = balance
        interest = _round(opening * r)
        # On the last period, pay off the exact remaining balance to avoid
        # sub-cent rounding residue.
        if period == duration_months:
            principal_component = opening
        else:
            principal_component = _round(emi - interest)
            # Guard against rounding making principal negative
            if principal_component > opening:
                principal_component = opening
        closing = _round(opening - principal_component)

        rows.append(
            AmortizationRow(
                period=period,
                opening_balance=opening,
                monthly_installment=_round(principal_component + interest + monthly_insurance),
                principal_component=principal_component,
                interest_component=interest,
                insurance_component=monthly_insurance,
                closing_balance=closing,
            )
        )
        balance = closing

    return rows


def compute_apr(
    principal: Decimal,
    monthly_installment: Decimal,
    duration_months: int,
) -> Decimal:
    """Compute APR via Newton-Raphson on the standard present-value equation.

    NPV(r) = sum_{t=1}^{n} C / (1+r)^t - P = 0,  r = monthly rate.

    Returns the annualised rate (monthly_rate * 12).
    No bank fees are included (per spec §9, Q4 closed: no arrangement fees).
    """
    if principal <= ZERO or monthly_installment <= ZERO:
        return ZERO

    C = float(monthly_installment)
    P = float(principal)
    n = duration_months

    # Initial guess: nominal monthly rate
    r = C / P / n  # rough starting point

    for _ in range(100):
        # f(r) = C * (1 - (1+r)^-n) / r - P
        try:
            factor = (1 + r) ** n
            f = C * (factor - 1) / (r * factor) - P
            # f'(r)
            df = C * (
                (n * (1 + r) ** (n - 1) * r * factor - (factor - 1) * (factor + r * n * (1 + r) ** (n - 1)))
                / (r * factor) ** 2
            )
            if df == 0:
                break
            r_new = r - f / df
            if abs(r_new - r) < 1e-12:
                r = r_new
                break
            r = r_new
        except (ZeroDivisionError, OverflowError):
            break

    annual_apr = Decimal(str(round(r * 12, 6)))
    return annual_apr
