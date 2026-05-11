"""Decimal-safe serialization helpers.

Converts domain dataclasses (which use decimal.Decimal) to JSON-safe dicts
where every Decimal appears as a string.  This prevents IEEE-754 float
precision loss in transit and round-trip corruption of financial values.
"""
from __future__ import annotations

import dataclasses
from decimal import Decimal
from typing import Any


def _convert(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _convert(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert(item) for item in obj]
    return obj


def to_json_safe(obj: Any) -> Any:
    """Convert a dataclass (or any value) to a JSON-serializable structure.

    Rules applied recursively:
    - dataclass  → dict  (via dataclasses.asdict, which recurses into nested dataclasses)
    - Decimal    → str
    - list/tuple → list
    - everything else passes through unchanged
    """
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return _convert(dataclasses.asdict(obj))
    return _convert(obj)
