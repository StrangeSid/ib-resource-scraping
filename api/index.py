"""Vercel entrypoint: re-export the FastAPI app.

Vercel's Python runtime looks for a FastAPI instance named `app` in
api/index.py (also accepts api/main.py, but an explicit entry is robust
against import-path quirks). Cloud mode is auto-selected because
store/index.sqlite is not deployed.
"""
from api.main import app  # noqa: F401
