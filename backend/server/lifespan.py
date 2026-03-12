from __future__ import annotations

"""ASGI lifespan wiring for server-shell app-scoped objects."""

from contextlib import asynccontextmanager
import logging
from typing import Any

from backend.api.cases_start import CaseRunRegistry, CaseStartService

from .config import ServerConfig
from .routes_http import build_ws_base_url
from .run_registry import RunRegistry
from .session_controller import SessionController

logger = logging.getLogger(__name__)


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
    app.state.shutting_down = False
    app.state.shutdown_note = ""
    app.state.startup_note = (
        f"server-shell started host={config.host}:{config.port} log_level={config.log_level}"
    )
    logger.info(
        "server-shell startup host=%s port=%s log_level=%s",
        config.host,
        config.port,
        config.log_level,
    )
    try:
        yield
    finally:
        app.state.started = False
        app.state.shutting_down = True
        app.state.shutdown_note = "server-shell shutting down"
        session_count = len(session_controller.list_sessions())
        run_count = run_registry.count()
        session_controller.begin_shutdown()
        session_controller.clear()
        run_registry.clear()
        logger.info(
            "server-shell shutdown sessions_cleared=%d runs_cleared=%d",
            session_count,
            run_count,
        )


__all__ = ["server_lifespan"]
