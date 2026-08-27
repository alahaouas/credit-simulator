"""Core financial calculation functions.

All monetary values use decimal.Decimal — float is forbidden.
Rounding: ROUND_HALF_UP to 2 decimal places for final outputs,
full precision for all intermediate steps.
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from functools import lru_cache

from .config import APR_MAX_ITERATIONS, APR_PRECISION, APR_TOLERANCE, CENT, MONTHS_IN_YEAR, ZERO


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
    if annual_rate < ZERO:
        raise ValueError("annual_rate must be >= 0")

    if annual_rate == ZERO:
        return _round(principal / Decimal(duration_months))

    r = annual_rate / MONTHS_IN_YEAR
    factor = (1 + r) ** int(duration_months)  # stays Decimal arithmetic
    emi = principal * r * factor / (factor - 1)
    return _round(emi)


def compute_monthly_insurance(
    original_principal: Decimal,
    annual_insurance_rate: Decimal,
) -> Decimal:
    """Fixed monthly insurance = original_principal * annual_rate / 12."""
    return _round(original_principal * annual_insurance_rate / MONTHS_IN_YEAR)


@lru_cache(maxsize=8192)
def compute_loan_plan(
    principal: Decimal,
    annual_interest_rate: Decimal,
    annual_insurance_rate: Decimal,
    duration_months: int,
) -> LoanPlan:
    """Compute the full loan plan summary (no amortization schedule).

    Memoized: the optimizer, the heatmap and the sweet-spot analysis all sweep
    overlapping (principal, rate, duration) grids within a single simulation,
    and LoanPlan is immutable so sharing instances is safe.
    """
    emi = compute_emi(principal, annual_interest_rate, duration_months)
    monthly_insurance = compute_monthly_insurance(principal, annual_insurance_rate)
    monthly_installment = _round(emi + monthly_insurance)

    # First month interest component
    r = annual_interest_rate / MONTHS_IN_YEAR
    monthly_interest_first = _round(principal * r)

    # Total interest follows the exact amortization rounding sequence (no accumulated
    # drift), but without materialising the schedule rows — this is the optimizer hot path.
    total_interest_paid = sum(
        (interest for _p, _o, _pc, interest, _c in _amortization_steps(
            principal, annual_interest_rate, duration_months
        )),
        ZERO,
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


def _amortization_steps(
    principal: Decimal,
    annual_interest_rate: Decimal,
    duration_months: int,
) -> Iterator[tuple[int, Decimal, Decimal, Decimal, Decimal]]:
    """Yield (period, opening, principal_component, interest, closing) month by month.

    Shared by build_amortization_schedule and compute_loan_plan so both derive
    interest from exactly the same rounding sequence. Allocates no row objects.
    """
    emi = compute_emi(principal, annual_interest_rate, duration_months)
    r = annual_interest_rate / MONTHS_IN_YEAR
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

        yield period, opening, principal_component, interest, closing
        balance = closing


def build_amortization_schedule(
    principal: Decimal,
    annual_interest_rate: Decimal,
    annual_insurance_rate: Decimal,
    duration_months: int,
) -> list[AmortizationRow]:
    """Build the full month-by-month amortization schedule."""
    monthly_insurance = compute_monthly_insurance(principal, annual_insurance_rate)

    return [
        AmortizationRow(
            period=period,
            opening_balance=opening,
            monthly_installment=_round(principal_component + interest + monthly_insurance),
            principal_component=principal_component,
            interest_component=interest,
            insurance_component=monthly_insurance,
            closing_balance=closing,
        )
        for period, opening, principal_component, interest, closing in _amortization_steps(
            principal, annual_interest_rate, duration_months
        )
    ]


def compute_apr(
    principal: Decimal,
    monthly_installment: Decimal,
    duration_months: int,
) -> Decimal:
    """Compute APR via Newton-Raphson on the standard present-value equation.

    NPV(r) = sum_{t=1}^{n} C / (1+r)^t - P = 0,  r = monthly rate.

    Returns the annualised rate (monthly_rate * 12).
    No bank fees are included (per spec §9, Q4 closed: no arrangement fees).

    All arithmetic uses Decimal throughout — float is never used.
    Convergence tolerance: 1e-12 (monthly rate).  Maximum 100 iterations.
    """
    if principal <= ZERO or monthly_installment <= ZERO:
        return ZERO

    C = monthly_installment
    P = principal
    n = duration_months
    _n = Decimal(n)

    # Initial guess: nominal monthly rate (P*r ≈ first-month interest ≈ C/n)
    r = C / P / _n

    for _ in range(APR_MAX_ITERATIONS):
        try:
            one_plus_r = 1 + r
            one_plus_r_n = one_plus_r ** n
            one_plus_r_n1 = one_plus_r_n / one_plus_r
            r_factor = r * one_plus_r_n

            # f(r) = C * ((1+r)^n - 1) / (r * (1+r)^n) - P
            f = C * (one_plus_r_n - 1) / r_factor - P

            # f'(r) via quotient rule, simplified for performance:
            # df = C * [ (1+r)^n * (1 - (1+r)^n) + r*n*(1+r)^(n-1) ] / (r * (1+r)^n)^2
            numerator = one_plus_r_n * (1 - one_plus_r_n) + r * _n * one_plus_r_n1
            df = C * numerator / (r_factor ** 2)

            if df == ZERO:
                break
            r_new = r - f / df
            if abs(r_new - r) < APR_TOLERANCE:
                r = r_new
                break
            r = r_new
        except (ZeroDivisionError, InvalidOperation):
            break

    annual_apr = (r * 12).quantize(APR_PRECISION, rounding=ROUND_HALF_UP)
    return annual_apr
