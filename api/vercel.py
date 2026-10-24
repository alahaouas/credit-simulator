"""Vercel entrypoint for the FastAPI service (``[tool.vercel] entrypoint`` in pyproject.toml).

The calculation engine lives in ``src/credit_simulator`` (src layout). Putting ``src``
on the import path makes it importable whether or not the build installed the
project package itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from api.main import app  # noqa: E402

__all__ = ["app"]
