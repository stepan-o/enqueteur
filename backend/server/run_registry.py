from __future__ import annotations

"""In-memory run registry shell for transport-layer orchestration."""

from threading import RLock
from typing import Any, Iterable, Mapping

from .errors import RunNotFoundError
from .models import RunLaunchMetadata, RunRegistryEntry


class RunRegistry:
    """Canonical in-memory registry for launched runs managed by the host layer."""

    def __init__(self) -> None:
        self._runs: dict[str, RunRegistryEntry] = {}
        self._lock = RLock()

    def register_launched_run(
        self,
        *,
        launch_payload: Mapping[str, Any],
        started_run: Any | None,
    ) -> RunRegistryEntry:
        launch = self._coerce_launch_metadata(launch_payload)
        prior = self.get(launch.run_id)
        entry = RunRegistryEntry.from_launch(
            launch=launch,
            started_run=started_run,
            metadata=dict(prior.metadata) if prior is not None else {},
        )
        if prior is not None:
            entry.host.registered_at = prior.host.registered_at
            entry.host.last_activity_at = prior.host.last_activity_at
            entry.host.last_session_id = prior.host.last_session_id
        self.put(entry)
        return entry

    def put(self, entry: RunRegistryEntry) -> None:
        with self._lock:
            self._runs[entry.run_id] = entry

    def get(self, run_id: str) -> RunRegistryEntry | None:
        with self._lock:
            return self._runs.get(run_id)

    def require(self, run_id: str) -> RunRegistryEntry:
        entry = self.get(run_id)
        if entry is None:
            raise RunNotFoundError(f"Run '{run_id}' is not registered.")
        return entry

    def exists(self, run_id: str) -> bool:
        return self.get(run_id) is not None

    def remove(self, run_id: str) -> RunRegistryEntry | None:
        with self._lock:
            return self._runs.pop(run_id, None)

    def list_runs(self) -> tuple[RunRegistryEntry, ...]:
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

    def resolve_connection_target(self, connection_target: str) -> RunRegistryEntry | None:
        from backend.api.cases_start import extract_run_id_from_connection_target

        run_id = extract_run_id_from_connection_target(connection_target)
        if run_id is None:
            return None
        return self.get(run_id)

    def get_launch_metadata(self, run_id: str) -> RunLaunchMetadata | None:
        entry = self.get(run_id)
        return entry.launch if entry is not None else None

    def get_runtime_reference(self, run_id: str) -> Any | None:
        entry = self.get(run_id)
        return entry.runtime.started_run if entry is not None else None

    def touch_activity(self, run_id: str, *, session_id: str | None = None) -> RunRegistryEntry:
        entry = self.require(run_id)
        entry.host.touch(session_id=session_id)
        self.put(entry)
        return entry

    @staticmethod
    def _coerce_launch_metadata(launch_payload: Mapping[str, Any]) -> RunLaunchMetadata:
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
        return RunLaunchMetadata(
            run_id=run_id,
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
            launch_payload=dict(launch_payload),
        )


__all__ = ["RunRegistry"]
