from __future__ import annotations

"""WebSocket server for sim_sim LIVE KVP endpoint (/kvp)."""

import asyncio
import logging
from typing import Any

from backend.sim_sim.live.session_host import ConnectionContext, SessionHost

logger = logging.getLogger(__name__)

try:
    from websockets.server import WebSocketServerProtocol, serve
except Exception:  # pragma: no cover - optional runtime dependency
    WebSocketServerProtocol = Any  # type: ignore[assignment]
    serve = None  # type: ignore[assignment]


class SimSimWsServer:
    def __init__(
        self,
        *,
        session_host: SessionHost,
        host: str = "127.0.0.1",
        port: int = 7777,
        route_path: str = "/kvp",
    ) -> None:
        self._session_host = session_host
        self._host = host
        self._port = int(port)
        self._route_path = route_path
        self._server = None

    async def start(self) -> None:
        if serve is None:
            raise RuntimeError(
                "websockets package is not installed. Install project dependencies before running --live."
            )
        self._server = await serve(self._on_client, self._host, self._port)
        logger.info("[live] ws listening on ws://%s:%s%s", self._host, self._port, self._route_path)

    async def stop(self) -> None:
        if self._server is None:
            return
        self._server.close()
        await self._server.wait_closed()
        self._server = None

    async def _on_client(self, websocket: WebSocketServerProtocol, path: str | None = None) -> None:
        route = path
        if route is None:
            req = getattr(websocket, "request", None)
            route = getattr(req, "path", None) or getattr(websocket, "path", None) or ""
        if route != self._route_path:
            await websocket.close(code=1008, reason=f"Expected {self._route_path}")
            return

        async def _send_bytes(data: bytes) -> None:
            await websocket.send(data)

        ctx: ConnectionContext = await self._session_host.register_connection(send_bytes=_send_bytes)
        try:
            async for message in websocket:
                if isinstance(message, bytes):
                    raw = message
                else:
                    raw = str(message).encode("utf-8")
                await self._session_host.handle_client_message(ctx, raw)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("[live] websocket handler error")
        finally:
            await self._session_host.unregister_connection(ctx)

