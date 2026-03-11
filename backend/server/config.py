from __future__ import annotations

"""Runtime config for the local Enqueteur ASGI server shell."""

from dataclasses import dataclass
import os


DEFAULT_ALLOWED_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
DEFAULT_UVICORN_APP_PATH = "backend.server.asgi:app"


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_int(value: str | None, *, default: int, minimum: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed >= minimum else default


def _parse_origins(value: str | None) -> tuple[str, ...]:
    if value is None:
        return DEFAULT_ALLOWED_ORIGINS
    parts = tuple(part.strip() for part in value.split(",") if part.strip())
    if not parts:
        return DEFAULT_ALLOWED_ORIGINS
    return parts


@dataclass(frozen=True)
class ServerConfig:
    """Transport/lifecycle host config (local-dev oriented)."""

    host: str = "127.0.0.1"
    port: int = 7777
    log_level: str = "info"
    allowed_origins: tuple[str, ...] = DEFAULT_ALLOWED_ORIGINS
    run_ttl_seconds: int = 60 * 30
    verbose_protocol_logging: bool = False

    def uvicorn_kwargs(self, *, app_path: str = DEFAULT_UVICORN_APP_PATH) -> dict[str, object]:
        return {
            "app": app_path,
            "factory": False,
            "host": self.host,
            "port": self.port,
            "log_level": self.log_level,
            "reload": False,
        }


def load_server_config(prefix: str = "ENQ_SERVER_") -> ServerConfig:
    """Build server config from env vars with safe local defaults."""

    host = os.getenv(f"{prefix}HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = _parse_int(os.getenv(f"{prefix}PORT"), default=7777, minimum=1)
    log_level = os.getenv(f"{prefix}LOG_LEVEL", "info").strip() or "info"
    origins = _parse_origins(os.getenv(f"{prefix}ALLOWED_ORIGINS"))
    run_ttl_seconds = _parse_int(os.getenv(f"{prefix}RUN_TTL_SECONDS"), default=60 * 30, minimum=1)
    verbose_protocol_logging = _parse_bool(
        os.getenv(f"{prefix}VERBOSE_PROTOCOL_LOGGING"),
        default=False,
    )
    return ServerConfig(
        host=host,
        port=port,
        log_level=log_level,
        allowed_origins=origins,
        run_ttl_seconds=run_ttl_seconds,
        verbose_protocol_logging=verbose_protocol_logging,
    )


__all__ = [
    "ServerConfig",
    "load_server_config",
    "DEFAULT_ALLOWED_ORIGINS",
    "DEFAULT_UVICORN_APP_PATH",
]
