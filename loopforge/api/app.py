from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.episodes import router as episodes_router


def create_app() -> FastAPI:
    """Create the FastAPI application for Loopforge Stage API.

    Base URL: http://localhost:8000
    - The CLI command `loopforge-sim api-server` launches uvicorn with this app.
    - By default, uvicorn binds to host 127.0.0.1 and port 8000; browsers may
      prefer http://localhost:8000. In local dev these resolve to the same.
    """
    app = FastAPI(title="Loopforge API", version="0.1", docs_url="/docs")

    # CORS for local Stage Viewer (Vite dev server on 5173)
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health probe for dev tooling and docker-compose
    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    # Read-only routers
    app.include_router(episodes_router, prefix="")

    return app


# ASGI entrypoint for uvicorn: "loopforge.api.app:app"
# Use: uvicorn loopforge.api.app:app --host 127.0.0.1 --port 8000
app = create_app()
