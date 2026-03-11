from __future__ import annotations

"""In-memory run registry shell for transport-layer orchestration."""

from threading import RLock
from typing import Iterable

from .errors import RunNotFoundError
from .models import RunRecord, new_id


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


__all__ = ["RunRegistry"]

