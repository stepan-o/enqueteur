from __future__ import annotations

"""In-memory run registry shell for transport-layer orchestration."""

from threading import RLock
from typing import Any, Iterable, Mapping

from .errors import RunNotFoundError
from .models import RunRecord, new_id, utc_now_iso


class RunRegistry:
    """Minimal run registry API for future launch/session binding."""

    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._lock = RLock()

    def create_placeholder_run(
        self,
        *,
        case_id: str | None = None,
        seed: str | int | None = None,
        difficulty_profile: str | None = None,
        mode: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> RunRecord:
        record = RunRecord(
            run_id=new_id(),
            case_id=case_id,
            seed=seed,
            difficulty_profile=difficulty_profile,
            mode=mode,
            metadata=dict(metadata or {}),
        )
        with self._lock:
            self._runs[record.run_id] = record
        return record

    def register_launched_run(
        self,
        *,
        launch_payload: Mapping[str, Any],
        started_run: Any | None,
    ) -> RunRecord:
        run_id = launch_payload.get("run_id")
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("launch_payload must include a non-empty string run_id.")

        world_id = launch_payload.get("world_id")
        case_id = launch_payload.get("case_id")
        seed = launch_payload.get("seed")
        resolved_seed_id = launch_payload.get("resolved_seed_id")
        difficulty_profile = launch_payload.get("difficulty_profile")
        mode = launch_payload.get("mode")
        engine_name = launch_payload.get("engine_name")
        schema_version = launch_payload.get("schema_version")
        ws_url = launch_payload.get("ws_url")
        started_at = launch_payload.get("started_at")

        prior = self.get(run_id)
        record = RunRecord(
            run_id=run_id,
            created_at=prior.created_at if prior is not None else utc_now_iso(),
            world_id=world_id if isinstance(world_id, str) else None,
            case_id=case_id if isinstance(case_id, str) else None,
            seed=seed if isinstance(seed, (str, int)) else None,
            resolved_seed_id=resolved_seed_id if isinstance(resolved_seed_id, str) else None,
            difficulty_profile=difficulty_profile if isinstance(difficulty_profile, str) else None,
            mode=mode if isinstance(mode, str) else None,
            engine_name=engine_name if isinstance(engine_name, str) else None,
            schema_version=schema_version if isinstance(schema_version, str) else None,
            ws_url=ws_url if isinstance(ws_url, str) else None,
            started_at=started_at if isinstance(started_at, str) else None,
            metadata=dict(prior.metadata) if prior is not None else {},
            launch_payload=dict(launch_payload),
            started_run=started_run,
        )
        self.put(record)
        return record

    def put(self, record: RunRecord) -> None:
        with self._lock:
            self._runs[record.run_id] = record

    def get(self, run_id: str) -> RunRecord | None:
        with self._lock:
            return self._runs.get(run_id)

    def require(self, run_id: str) -> RunRecord:
        record = self.get(run_id)
        if record is None:
            raise RunNotFoundError(f"Run '{run_id}' is not registered.")
        return record

    def remove(self, run_id: str) -> RunRecord | None:
        with self._lock:
            return self._runs.pop(run_id, None)

    def list_runs(self) -> tuple[RunRecord, ...]:
        with self._lock:
            return tuple(self._runs.values())

    def count(self) -> int:
        with self._lock:
            return len(self._runs)

    def clear(self) -> None:
        with self._lock:
            self._runs.clear()

    def iter_run_ids(self) -> Iterable[str]:
        with self._lock:
            return tuple(self._runs.keys())

    def resolve_connection_target(self, connection_target: str) -> RunRecord | None:
        from backend.api.cases_start import extract_run_id_from_connection_target

        run_id = extract_run_id_from_connection_target(connection_target)
        if run_id is None:
            return None
        return self.get(run_id)


__all__ = ["RunRegistry"]
