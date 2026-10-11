"""Root entrypoint for Vercel's FastAPI preset (mirrors vercel/examples).

Single root-level `app` candidate so the build serves the whole
application as one function: UI at `/`, API at `/search`, `/stats`, …
Local dev is unchanged (`uvicorn api.main:app`).
"""
from api.main import app  # noqa: F401
