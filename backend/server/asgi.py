from __future__ import annotations

"""Canonical ASGI app object for local Uvicorn execution."""

from .app import create_app

# Canonical Uvicorn target: backend.server.asgi:app
app = create_app()

