"""Online rate fetcher — ECB / Bank of England / FRED (§5.4).

Only fetches annual_rate for the 'average' quality.
All fetches are user-triggered (no background polling).
"""
from __future__ import annotations

import os
from decimal import Decimal

import requests

# Timeout for HTTP calls (seconds)
_TIMEOUT = 10

# ECB country codes that use the MIR series
_ECB_COUNTRIES = frozenset({"BE", "FR", "DE", "ES", "IT", "PT"})

# ECB Data Portal endpoint template
# Series: MIR.M.{CC}.B.A2C.F.R.A.2250.EUR.N
# monthly · country · new business · housing loans · annualised agreed rate · households · EUR
_ECB_URL = (
    "https://data.ecb.europa.eu/api/v1/data/MIR/"
    "M.{cc}.B.A2C.F.R.A.2250.EUR.N"
    "?lastNObservations=1&format=jsondata"
)

# Bank of England — effective mortgage rate (BoE IRS series IUMTLMV)
_BOE_URL = (
    "https://www.bankofengland.co.uk/boeapps/database/fromshowcolumns.asp"
    "?Travel=NIxRSxSUx&FromSeries=1&ToSeries=50&DAT=RNG"
    "&FD=1&FM=Jan&FY=2024&TD=31&TM=Dec&TY=2025"
    "&VFD=Y&html.x=66&html.y=26&C=IUM&Filter=N"
)

# FRED — 30-year fixed mortgage rate
_FRED_SERIES = "MORTGAGE30US"
_FRED_URL = "https://api.stlouisfed.org/fred/series/observations"


class FetchError(Exception):
    """Raised when an online rate fetch fails for any reason."""


def fetch_rate(country: str) -> Decimal:
    """Fetch the latest average annual mortgage rate for *country*.

    Returns the rate as a Decimal fraction (e.g. 0.035 for 3.5%).
    Raises FetchError on any error (network, parsing, missing data).
    """
    code = country.upper()
    if code in _ECB_COUNTRIES:
        return _fetch_ecb(code)
    elif code == "GB":
        return _fetch_boe()
    elif code == "US":
        return _fetch_fred()
    else:
        raise FetchError(
            f"No online data source configured for country '{code}'. "
            "Please update the rate manually."
        )


def _fetch_ecb(country_code: str) -> Decimal:
    url = _ECB_URL.format(cc=country_code)
    try:
        resp = requests.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise FetchError(f"ECB API request failed: {exc}") from exc

    try:
        data = resp.json()
        # ECB JSON-stat-2 format: dataSets[0].series["0:0:0:0:0:0:0:0:0:0:0"].observations
        series = data["dataSets"][0]["series"]
        # There should be exactly one series key
        series_key = next(iter(series))
        observations = series[series_key]["observations"]
        # lastNObservations=1 → only one observation
        obs_key = next(iter(observations))
        value = observations[obs_key][0]  # annualised rate in percent
        if value is None:
            raise FetchError(f"ECB returned null value for {country_code}.")
        # ECB returns percentage (e.g. 3.5), convert to fraction
        rate = Decimal(str(value)) / Decimal("100")
        return rate
    except (KeyError, IndexError, StopIteration, TypeError) as exc:
        raise FetchError(f"Failed to parse ECB response for {country_code}: {exc}") from exc


def _fetch_boe() -> Decimal:
    """Fetch GB effective mortgage rate from Bank of England.

    Uses the BoE Statistics API (series IUMTLMV — effective rate on new mortgages).
    """
    url = (
        "https://www.bankofengland.co.uk/boeapps/database/_iadb-FromShowColumns.asp"
        "?csv.x=yes&Datefrom=01/Jan/2024&Dateto=now&SeriesCodes=IUMTLMV&CSVF=TT&UsingCodes=Y"
    )
    try:
        resp = requests.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise FetchError(f"Bank of England API request failed: {exc}") from exc

    try:
        lines = resp.text.strip().splitlines()
        # CSV: DATE,IUMTLMV — take last data row
        last_value = None
        for line in lines[1:]:  # skip header
            parts = line.split(",")
            if len(parts) >= 2 and parts[1].strip():
                last_value = parts[1].strip()
        if last_value is None:
            raise FetchError("No data returned from Bank of England.")
        # BoE returns percentage
        rate = Decimal(last_value) / Decimal("100")
        return rate
    except (IndexError, ValueError) as exc:
        raise FetchError(f"Failed to parse Bank of England response: {exc}") from exc


def _fetch_fred() -> Decimal:
    """Fetch US 30-year fixed mortgage rate from FRED."""
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise FetchError(
            "FRED_API_KEY environment variable is not set. "
            "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    params = {
        "series_id": _FRED_SERIES,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1,
    }
    try:
        resp = requests.get(_FRED_URL, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise FetchError(f"FRED API request failed: {exc}") from exc

    try:
        data = resp.json()
        observations = data["observations"]
        if not observations:
            raise FetchError("FRED returned no observations.")
        value_str = observations[0]["value"]
        if value_str == ".":
            raise FetchError("FRED returned missing value ('.').")
        rate = Decimal(value_str) / Decimal("100")
        return rate
    except (KeyError, IndexError, ValueError) as exc:
        raise FetchError(f"Failed to parse FRED response: {exc}") from exc
