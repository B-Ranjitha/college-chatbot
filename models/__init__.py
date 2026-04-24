"""
models/__init__.py
------------------
Makes `models` a proper Python package so that
  from models.db import init_db, get_conn, ...
works from any directory depth.

Exposes a single convenience accessor `get_db` that returns
the module-level connection helper — useful if other packages
need to call raw SQL without importing db directly.
"""

from models.db import get_conn as get_db   # noqa: F401  — re-exported for convenience

__all__ = ["get_db"]

