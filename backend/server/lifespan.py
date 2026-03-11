from __future__ import annotations

"""ASGI lifespan wiring for server-shell app-scoped objects."""

from contextlib import asynccontextmanager
from typing import Any

from backend.api.cases_start import CaseRunRegistry, CaseStartService

from .config import ServerConfig
from .routes_http import build_ws_base_url
from .run_registry import RunRegistry
from .session_controller import SessionController


@asynccontextmanager
async def server_lifespan(app: Any):
    """Initialize transport-layer singletons for local runtime hosting."""

    config: ServerConfig = app.state.server_config
    run_registry = RunRegistry()
    session_controller = SessionController(run_registry=run_registry)
    case_start_service = CaseStartService(
        ws_base_url=build_ws_base_url(config),
        registry=CaseRunRegistry(),
    )

    app.state.run_registry = run_registry
    app.state.session_controller = session_controller
    app.state.case_start_service = case_start_service
    app.state.started = True
    app.state.startup_note = (
        f"server-shell started host={config.host}:{config.port} log_level={config.log_level}"
    )
    try:
        yield
    finally:
        # S3: minimal safe teardown scaffolding only.
        app.state.started = False
        session_controller.clear()
        run_registry.clear()


__all__ = ["server_lifespan"]
