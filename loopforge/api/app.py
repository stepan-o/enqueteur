from __future__ import annotations

from fastapi import FastAPI

from .routers.episodes import router as episodes_router


def create_app() -> FastAPI:
    app = FastAPI(title="Loopforge API", version="0.1", docs_url="/docs")

    # Read-only routers
    app.include_router(episodes_router, prefix="")

    return app


# ASGI entrypoint for uvicorn: "loopforge.api.app:app"
app = create_app()
