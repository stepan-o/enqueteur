from __future__ import annotations

"""
Run & Episode Registry (Sprint R1)

Append-only, file-backed JSONL registry that records each episode summarized
via the CLI. Lives strictly above the seam; has no impact on simulation
mechanics or log schemas.

Public API:
- EpisodeRecord dataclass
- registry_path(base_dir: Path | None = None) -> Path
- append_episode_record(record: EpisodeRecord, base_dir: Path | None = None) -> None
- load_registry(base_dir: Path | None = None) -> list[EpisodeRecord]

Notes:
- Fail-soft on I/O; malformed lines are skipped during load.
- Default path is logs/loopforge_run_registry.jsonl.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
import json

REGISTRY_FILENAME = "loopforge_run_registry.jsonl"


@dataclass
class EpisodeRecord:
    run_id: str
    episode_id: str
    episode_index: int
    created_at: str  # ISO 8601
    steps_per_day: int
    days: int
    # Optional fields for future extension (kept None by default)
    scenario_name: Optional[str] = None
    # Sprint 1 additions (backward compatible, default None)
    status: Optional[str] = None  # e.g., "resolved", "orphaned" (not enforced yet)
    source: Optional[str] = None  # e.g., "simulation", "cli-view-episode"

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "episode_id": self.episode_id,
            "episode_index": int(self.episode_index),
            "created_at": str(self.created_at),
            "steps_per_day": int(self.steps_per_day),
            "days": int(self.days),
            "scenario_name": self.scenario_name,
            "status": self.status,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EpisodeRecord":
        return cls(
            run_id=str(d.get("run_id", "")),
            episode_id=str(d.get("episode_id", "")),
            episode_index=int(d.get("episode_index", 0) or 0),
            created_at=str(d.get("created_at", "")),
            steps_per_day=int(d.get("steps_per_day", 0) or 0),
            days=int(d.get("days", 0) or 0),
            scenario_name=d.get("scenario_name"),
            status=d.get("status"),
            source=d.get("source"),
        )


def registry_path(base_dir: Path | None = None) -> Path:
    """Return the full path to the registry JSONL file.

    Default location is logs/loopforge_run_registry.jsonl relative to CWD.
    """
    if base_dir is None:
        return Path("logs") / REGISTRY_FILENAME
    return Path(base_dir) / REGISTRY_FILENAME


def append_episode_record(record: EpisodeRecord, base_dir: Path | None = None) -> None:
    """Append a single EpisodeRecord as a JSON line to the registry file.

    Creates parent directories if missing. Fail-soft on I/O errors.
    """
    path = registry_path(base_dir)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), separators=(",", ":")))
            f.write("\n")
    except Exception:
        # Do not propagate errors; registry must never break CLI flows
        pass


def load_registry(base_dir: Path | None = None) -> List[EpisodeRecord]:
    """Load all EpisodeRecord rows from the registry file.

    Fail-soft: if file missing or unreadable, return what we could parse.
    Malformed lines are skipped.
    """
    path = registry_path(base_dir)
    if not path.exists():
        return []
    out: List[EpisodeRecord] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    if isinstance(d, dict):
                        out.append(EpisodeRecord.from_dict(d))
                except Exception:
                    # skip malformed
                    continue
    except Exception:
        return out
    return out


def find_episode_record(run_id: str, episode_index: int = 0, *, base_dir: Path | None = None) -> Optional[EpisodeRecord]:
    """Return the latest EpisodeRecord matching (run_id, episode_index).

    Since the registry is append-only, we pick the last match to reflect the
    most recent recording for that identity pair.
    """
    rows = load_registry(base_dir=base_dir)
    match: Optional[EpisodeRecord] = None
    for r in rows:
        try:
            if r.run_id == run_id and int(getattr(r, "episode_index", 0) or 0) == int(episode_index):
                match = r
        except Exception:
            continue
    return match


def latest_episode_record(*, base_dir: Path | None = None) -> Optional[EpisodeRecord]:
    """Return the most recently appended EpisodeRecord, or None if empty."""
    rows = load_registry(base_dir=base_dir)
    return rows[-1] if rows else None


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 string format."""
    try:
        return datetime.now(timezone.utc).isoformat()
    except Exception:
        # Fallback to naive ISO format if timezone support is unavailable
        return datetime.utcnow().isoformat()
