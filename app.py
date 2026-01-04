"""Root-level FastAPI entrypoint for auto-discovery by uvicorn/FastAPI.

This module re-exports the FastAPI app from web.backend.app so that
tools like uvicorn can automatically discover and run it without
explicit module path specification.
"""

from __future__ import annotations

from web.backend.app import app

__all__ = ["app"]
