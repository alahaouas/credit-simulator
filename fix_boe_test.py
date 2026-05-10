import re
with open('tests/unit/test_fetcher.py', 'r') as f:
    content = f.read()

old_test = """
    def test_boe_value_error_raises(self):
        \"\"\"A ValueError raised during BoE response text processing should trigger FetchError.\"\"\"
        from unittest.mock import PropertyMock
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_resp = MagicMock()
            type(mock_resp).text = PropertyMock(side_effect=ValueError("Bad CSV format"))
            mock_get.return_value = mock_resp
            with pytest.raises(FetchError, match="Failed to parse Bank of England response"):
                fetch_rate("GB")
"""

new_test = """
    def test_boe_value_error_raises(self):
        \"\"\"Simulate a parsing error (like ValueError/InvalidOperation) using a malformed response.\"\"\"
        # A CSV with a bad numeric format will trigger an error when parsing the rate.
        bad_csv = "DATE,IUMTLMV\\n01/Jan/2024,NOT_A_NUMBER\\n"
        with patch("credit_simulator.fetcher.requests.get") as mock_get:
            mock_get.return_value = _mock_response(text=bad_csv)
            with pytest.raises(FetchError, match="Failed to parse Bank of England response"):
                fetch_rate("GB")
"""

content = content.replace(old_test, new_test)

with open('tests/unit/test_fetcher.py', 'w') as f:
    f.write(content)
