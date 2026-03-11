from __future__ import annotations

"""ASGI app factory for Enqueteur local transport host shell."""

from typing import Any

from .config import ServerConfig, load_server_config
from .lifespan import server_lifespan
from .routes_http import register_http_routes
from .routes_ws import register_ws_routes


def create_app(config: ServerConfig | None = None) -> Any:
    """Create and configure the server-shell ASGI app."""

    resolved_config = config if config is not None else load_server_config()

    # Import framework lazily so repo imports remain clean without FastAPI installed.
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(
        title="Enqueteur Server Shell",
        version="0.1.0",
        lifespan=server_lifespan,
    )
    app.state.server_config = resolved_config

    if resolved_config.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(resolved_config.allowed_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    register_http_routes(app)
    register_ws_routes(app)
    return app


def run_dev(config: ServerConfig | None = None) -> None:
    """Run local uvicorn host for server-shell manual testing."""

    resolved_config = config if config is not None else load_server_config()
    import uvicorn

    uvicorn.run(**resolved_config.uvicorn_kwargs())
