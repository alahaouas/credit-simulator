"""Unit tests for fetcher.py — mocked HTTP responses for ECB, BoE, and FRED."""
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from credit_simulator.fetcher import FetchError, fetch_rate

# ── Helpers ────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_fetch_rate_cache():
    """Clear the LRU cache on fetch_rate before each test to ensure mocked requests are made."""
    fetch_rate.cache_clear()


def _mock_response(json_data=None, text=None, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    if text is not None:
        resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


# ── ECB tests ─────────────────────────────────────────────────────────────────

_ECB_JSON = {
    "dataSets": [
        {
            "series": {
                "0:0:0:0:0:0:0:0:0:0:0": {
                    "observations": {
                        "0": [3.5, 0]
                    }
                }
            }
        }
    ]
}


class TestFetchECB:
    @pytest.mark.parametrize("country", ["FR", "DE", "ES", "IT", "PT"])
    def test_ecb_country_returns_rate(self, country):
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_get.return_value = _mock_response(json_data=_ECB_JSON)
            rate = fetch_rate(country)
        assert rate == Decimal("0.035")

    def test_ecb_converts_percent_to_fraction(self):
        """ECB returns percent (3.5), must be returned as fraction (0.035)."""
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_get.return_value = _mock_response(json_data=_ECB_JSON)
            rate = fetch_rate("FR")
        assert rate == Decimal("3.5") / Decimal("100")

    def test_ecb_null_value_raises(self):
        bad_json = {
            "dataSets": [
                {
                    "series": {
                        "0:0:0:0:0:0:0:0:0:0:0": {
                            "observations": {"0": [None]}
                        }
                    }
                }
            ]
        }
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_get.return_value = _mock_response(json_data=bad_json)
            with pytest.raises(FetchError, match="null value"):
                fetch_rate("FR")

    def test_ecb_malformed_json_raises(self):
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_get.return_value = _mock_response(json_data={"unexpected": True})
            with pytest.raises(FetchError, match="Failed to parse ECB response"):
                fetch_rate("FR")

    def test_ecb_network_error_raises(self):
        import requests as _requests
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_get.side_effect = _requests.RequestException("timeout")
            with pytest.raises(FetchError, match="ECB API request failed"):
                fetch_rate("FR")


# ── BoE tests ─────────────────────────────────────────────────────────────────

_BOE_CSV = "DATE,IUMTLMV\n01/Jan/2024,4.80\n01/Feb/2024,4.75\n01/Mar/2024,\n"


class TestFetchBoE:
    def test_boe_returns_last_non_empty_row(self):
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_get.return_value = _mock_response(text=_BOE_CSV)
            rate = fetch_rate("GB")
        # Last row with a value is Feb 2024: 4.75%
        assert rate == Decimal("4.75") / Decimal("100")

    def test_boe_converts_percent_to_fraction(self):
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_get.return_value = _mock_response(text=_BOE_CSV)
            rate = fetch_rate("GB")
        assert rate == Decimal("0.0475")

    def test_boe_missing_column_raises(self):
        """If the IUMTLMV column is absent the parser must raise FetchError."""
        bad_csv = "DATE,OTHER_SERIES\n01/Jan/2024,5.0\n"
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_get.return_value = _mock_response(text=bad_csv)
            with pytest.raises(FetchError, match="IUMTLMV"):
                fetch_rate("GB")

    def test_boe_empty_body_raises(self):
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_get.return_value = _mock_response(text="DATE,IUMTLMV\n")
            with pytest.raises(FetchError, match="No data returned"):
                fetch_rate("GB")

    def test_boe_network_error_raises(self):
        import requests as _requests
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_get.side_effect = _requests.RequestException("connection refused")
            with pytest.raises(FetchError, match="Bank of England API request failed"):
                fetch_rate("GB")

    def test_boe_parsing_error_raises(self):
        """Malformed numeric value in BoE response should trigger FetchError (via ValueError)."""
        bad_csv = "DATE,IUMTLMV\n01/Jan/2024,INVALID\n"
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_get.return_value = _mock_response(text=bad_csv)
            with pytest.raises(FetchError, match="Failed to parse Bank of England response"):
                fetch_rate("GB")


# ── FRED tests ────────────────────────────────────────────────────────────────

_FRED_JSON = {
    "observations": [
        {"date": "2024-03-14", "value": "6.87"}
    ]
}


class TestFetchFRED:
    def test_fred_returns_rate(self):
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_get.return_value = _mock_response(json_data=_FRED_JSON)
            with patch.dict("os.environ", {"FRED_API_KEY": "test_key"}):
                rate = fetch_rate("US")
        assert rate == Decimal("6.87") / Decimal("100")

    def test_fred_missing_api_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            # Ensure FRED_API_KEY is absent
            import os
            os.environ.pop("FRED_API_KEY", None)
            with pytest.raises(FetchError, match="FRED_API_KEY"):
                fetch_rate("US")

    def test_fred_missing_value_raises(self):
        bad_json = {"observations": [{"date": "2024-03-14", "value": "."}]}
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_get.return_value = _mock_response(json_data=bad_json)
            with patch.dict("os.environ", {"FRED_API_KEY": "test_key"}):
                with pytest.raises(FetchError, match="missing value"):
                    fetch_rate("US")

    def test_fred_empty_observations_raises(self):
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_get.return_value = _mock_response(json_data={"observations": []})
            with patch.dict("os.environ", {"FRED_API_KEY": "test_key"}):
                with pytest.raises(FetchError, match="no observations"):
                    fetch_rate("US")

    def test_fred_network_error_raises(self):
        import requests as _requests
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_get.side_effect = _requests.RequestException("timeout")
            with patch.dict("os.environ", {"FRED_API_KEY": "test_key"}):
                with pytest.raises(FetchError, match="FRED API request failed"):
                    fetch_rate("US")


# ── Unsupported country ────────────────────────────────────────────────────────

class TestFetchUnsupportedCountry:
    def test_be_raises_no_source_configured(self):
        """BE has no online data source — fetch_rate must raise FetchError."""
        with pytest.raises(FetchError, match="No online data source"):
            fetch_rate("BE")

    def test_unknown_code_raises(self):
        with pytest.raises(FetchError, match="No online data source"):
            fetch_rate("ZZ")
