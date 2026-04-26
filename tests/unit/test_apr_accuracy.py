from decimal import Decimal

from credit_simulator.calculator import compute_apr


def test_apr_consistency():
    """
    Test that compute_apr remains consistent and accurate across a variety of inputs.
    This ensures the optimized logic (mathematical simplification) holds.
    """
    test_cases = [
        # principal, monthly_installment, duration, expected_at_least
        (Decimal("100000"), Decimal("500"), 360, Decimal("0.04")),
        (Decimal("200000"), Decimal("1500"), 240, Decimal("0.06")),
        (Decimal("50000"), Decimal("1000"), 60, Decimal("0.07")),
        (Decimal("10000"), Decimal("100"), 120, Decimal("0.03")),
    ]

    for p, mi, d, min_expected in test_cases:
        apr = compute_apr(p, mi, d)
        assert apr > min_expected
        # Verify it converges to something sensible (less than 100% APR for these cases)
        assert apr < Decimal("1.0")

def test_apr_edge_cases():
    """Test extreme interest rate scenarios."""
    # Very high interest rate
    # P=1000, installment=200, duration=10 -> clearly very high APR
    apr_high = compute_apr(Decimal("1000"), Decimal("200"), 10)
    assert apr_high > Decimal("1.0") # > 100% APR

    # Very low interest rate (but not zero)
    # P=1200, installment=101, duration=12 -> almost zero interest (12*101 = 1212)
    apr_low = compute_apr(Decimal("1200"), Decimal("101"), 12)
    assert Decimal("0") < apr_low < Decimal("0.02")

def test_apr_mathematical_identity():
    """
    Verify the simplified formula matches the expected output for a known case.
    Nominal rate 3.5%, monthly installment computed for 100k, 20 years.
    """
    principal = Decimal("100000")
    # At 3.5% nominal, monthly rate r = 0.035 / 12
    # EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    r_nom = Decimal("0.035") / 12
    n = 240
    one_plus_r_n = (1 + r_nom) ** n
    emi = (principal * r_nom * one_plus_r_n / (one_plus_r_n - 1)).quantize(Decimal("0.01"))

    # Now compute APR from this EMI
    apr = compute_apr(principal, emi, n)

    # APR should be very close to 3.5% (annualized nominal)
    assert abs(apr - Decimal("0.035")) < Decimal("0.0001")
