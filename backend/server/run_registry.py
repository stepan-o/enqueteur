from __future__ import annotations

"""In-memory run registry shell for transport-layer orchestration."""

from datetime import UTC, datetime, timedelta
import logging
from threading import RLock
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qs, urlparse

from .errors import RunNotFoundError
from .models import RunLaunchMetadata, RunRegistryEntry

DEFAULT_STALE_RUN_TTL_SECONDS = 60 * 30
logger = logging.getLogger(__name__)


class RunRegistry:
    """Canonical in-memory registry for launched runs managed by the host layer."""

    def __init__(self, *, stale_run_ttl_seconds: int = DEFAULT_STALE_RUN_TTL_SECONDS) -> None:
        self._runs: dict[str, RunRegistryEntry] = {}
        self._lock = RLock()
        self._stale_run_ttl_seconds = max(1, int(stale_run_ttl_seconds))

    def register_launched_run(
        self,
        *,
        launch_payload: Mapping[str, Any],
        started_run: Any | None,
    ) -> RunRegistryEntry:
        self.evict_stale_runs()
        launch = self._coerce_launch_metadata(launch_payload)
        prior = self._get_without_eviction(launch.run_id)
        entry = RunRegistryEntry.from_launch(
            launch=launch,
            started_run=started_run,
        )
        if prior is not None:
            entry.host.registered_at = prior.host.registered_at
            entry.host.last_activity_at = prior.host.last_activity_at
            entry.host.last_session_id = prior.host.last_session_id
            entry.host.active_session_id = prior.host.active_session_id
            entry.host.detached_at = prior.host.detached_at
        self.put(entry)
        return entry

    def put(self, entry: RunRegistryEntry) -> None:
        with self._lock:
            self._runs[entry.run_id] = entry

    def get(self, run_id: str) -> RunRegistryEntry | None:
        self.evict_stale_runs()
        with self._lock:
            return self._runs.get(run_id)

    def get_by_connection_target(self, connection_target: str) -> RunRegistryEntry | None:
        run_id = self.extract_run_id(connection_target)
        if run_id is None:
            return None
        return self.get(run_id)

    def require(self, run_id: str) -> RunRegistryEntry:
        entry = self.get(run_id)
        if entry is None:
            raise RunNotFoundError(f"Run '{run_id}' is not registered.")
        return entry

    def exists(self, run_id: str) -> bool:
        return self.get(run_id) is not None

    def remove(self, run_id: str) -> RunRegistryEntry | None:
        self.evict_stale_runs()
        with self._lock:
            return self._runs.pop(run_id, None)

    def list_runs(self) -> tuple[RunRegistryEntry, ...]:
        self.evict_stale_runs()
        with self._lock:
            return tuple(self._runs.values())

    def count(self) -> int:
        self.evict_stale_runs()
        with self._lock:
            return len(self._runs)

    def clear(self) -> None:
        with self._lock:
            self._runs.clear()

    def iter_run_ids(self) -> Iterable[str]:
        self.evict_stale_runs()
        with self._lock:
            return tuple(self._runs.keys())

    def resolve_connection_target(self, connection_target: str) -> RunRegistryEntry | None:
        # Backward-compatible alias. Prefer get_by_connection_target for new code.
        return self.get_by_connection_target(connection_target)

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

    def attach_session(self, run_id: str, *, session_id: str) -> RunRegistryEntry:
        entry = self.require(run_id)
        entry.host.attach(session_id=session_id)
        self.put(entry)
        return entry

    def detach_session(self, run_id: str, *, session_id: str | None = None) -> RunRegistryEntry | None:
        self.evict_stale_runs()
        entry = self._get_without_eviction(run_id)
        if entry is None:
            return None
        entry.host.detach(session_id=session_id)
        self.put(entry)
        return entry

    def evict_stale_runs(self) -> tuple[str, ...]:
        with self._lock:
            now = datetime.now(UTC)
            cutoff = now - timedelta(seconds=self._stale_run_ttl_seconds)
            stale_run_ids: list[str] = []
            for run_id, entry in self._runs.items():
                if entry.host.active_session_id is not None:
                    continue
                activity_at = _parse_iso_utc(entry.host.detached_at) or _parse_iso_utc(entry.host.last_activity_at)
                if activity_at is None:
                    continue
                if activity_at <= cutoff:
                    stale_run_ids.append(run_id)
            for run_id in stale_run_ids:
                self._runs.pop(run_id, None)
        if stale_run_ids:
            sample = ",".join(stale_run_ids[:3])
            logger.info(
                "run registry evicted stale detached runs count=%d sample_run_ids=%s ttl_seconds=%d",
                len(stale_run_ids),
                sample,
                self._stale_run_ttl_seconds,
            )
        return tuple(stale_run_ids)

    @staticmethod
    def extract_run_id(connection_target: str) -> str | None:
        """Resolve canonical run_id from a connection target or raw id string."""
        text = connection_target.strip()
        if not text:
            return None
        if "://" not in text and "?" not in text and "/" not in text:
            return text

        parsed = urlparse(text)
        run_ids = parse_qs(parsed.query).get("run_id", [])
        if not run_ids:
            return None
        run_id = run_ids[0].strip()
        return run_id if isinstance(run_id, str) and run_id else None

    @staticmethod
    def _coerce_launch_metadata(launch_payload: Mapping[str, Any]) -> RunLaunchMetadata:
        run_id = launch_payload.get("run_id")
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("launch_payload must include a non-empty string run_id.")
        normalized_run_id = run_id.strip()

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
        parsed_ws_run_id = (
            RunRegistry.extract_run_id(ws_url)
            if isinstance(ws_url, str) and ws_url
            else None
        )
        if parsed_ws_run_id is not None and parsed_ws_run_id != normalized_run_id:
            raise ValueError("launch_payload ws_url run_id must match launch_payload run_id.")

        return RunLaunchMetadata(
            run_id=normalized_run_id,
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
        )

    def _get_without_eviction(self, run_id: str) -> RunRegistryEntry | None:
        with self._lock:
            return self._runs.get(run_id)


def _parse_iso_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


__all__ = ["RunRegistry"]
