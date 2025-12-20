from __future__ import annotations

"""Run/session determinism anchors (SSoT for exports).

This module defines the immutable, serializable anchors required to identify a run
and reproduce viewer-deterministic playback. It performs strict validation and
enforces schema_version equality with INTEGRATION_SCHEMA_VERSION.
"""

from dataclasses import dataclass
from typing import Dict, Any
import uuid as _uuid

from .schema_version import INTEGRATION_SCHEMA_VERSION


def _require_uuid_str(value: str, field: str) -> str:
    """Lightweight UUID-ish validation: must parse as UUID string."""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string UUID")
    try:
        _uuid.UUID(value)
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"{field} must be a valid UUID string") from e
    return value


@dataclass(frozen=True)
class RunAnchors:
    engine_name: str
    engine_version: str
    schema_version: str
    world_id: str  # uuid string
    run_id: str  # uuid string
    seed: int
    tick_rate_hz: int
    time_origin_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_name": self.engine_name,
            "engine_version": self.engine_version,
            "schema_version": self.schema_version,
            "world_id": self.world_id,
            "run_id": self.run_id,
            "seed": int(self.seed),
            "tick_rate_hz": int(self.tick_rate_hz),
            "time_origin_ms": int(self.time_origin_ms),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RunAnchors":
        if not isinstance(d, dict):
            raise ValueError("RunAnchors.from_dict requires a dict input")

        required = [
            "engine_name",
            "engine_version",
            "schema_version",
            "world_id",
            "run_id",
            "seed",
            "tick_rate_hz",
            "time_origin_ms",
        ]
        missing = [k for k in required if k not in d]
        if missing:
            raise ValueError(f"Missing required RunAnchors fields: {', '.join(missing)}")

        engine_name = d["engine_name"]
        engine_version = d["engine_version"]
        schema_version = d["schema_version"]
        if not isinstance(engine_name, str) or not engine_name:
            raise ValueError("engine_name must be a non-empty string")
        if not isinstance(engine_version, str) or not engine_version:
            raise ValueError("engine_version must be a non-empty string")
        if not isinstance(schema_version, str) or not schema_version:
            raise ValueError("schema_version must be a non-empty string")
        if schema_version != INTEGRATION_SCHEMA_VERSION:
            raise ValueError(
                "schema_version mismatch with INTEGRATION_SCHEMA_VERSION"
            )

        world_id = _require_uuid_str(d["world_id"], "world_id")
        run_id = _require_uuid_str(d["run_id"], "run_id")

        try:
            seed = int(d["seed"])
        except Exception as e:  # noqa: BLE001
            raise ValueError("seed must be an integer") from e

        try:
            tick_rate_hz = int(d["tick_rate_hz"])
        except Exception as e:  # noqa: BLE001
            raise ValueError("tick_rate_hz must be an integer") from e
        if tick_rate_hz <= 0:
            raise ValueError("tick_rate_hz must be > 0")

        try:
            time_origin_ms = int(d["time_origin_ms"])
        except Exception as e:  # noqa: BLE001
            raise ValueError("time_origin_ms must be an integer") from e
        if time_origin_ms < 0:
            raise ValueError("time_origin_ms must be >= 0")

        return RunAnchors(
            engine_name=engine_name,
            engine_version=engine_version,
            schema_version=schema_version,
            world_id=world_id,
            run_id=run_id,
            seed=seed,
            tick_rate_hz=tick_rate_hz,
            time_origin_ms=time_origin_ms,
        )


__all__ = ["RunAnchors"]
