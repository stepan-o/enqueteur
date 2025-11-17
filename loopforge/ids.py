from __future__ import annotations

"""
Identity helpers (Sprint E2)

Pure, above-the-seam utilities for generating and carrying run/episode identity.
No side effects; no log schema changes.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
import uuid


@dataclass(frozen=True)
class RunContext:
    run_id: str
    created_at: datetime
    seed: Optional[int] = None
    scenario_name: Optional[str] = None


@dataclass(frozen=True)
class EpisodeIdentity:
    run_id: str
    episode_id: str
    episode_index: int


def generate_run_id() -> str:
    """Return a unique-enough run identifier.

    Deterministic enough for our purposes: UUID4 hex string.
    We intentionally avoid time-based entropy to keep it simple and
    independent from system clock in tests that mock UUIDs.
    """
    return uuid.uuid4().hex


def generate_episode_id(run_id: str, episode_index: int) -> str:
    """Generate an episode identifier scoped by run and index.

    Pattern: "{run_id[:8]}-{episode_index:04d}-{uuid4hex8}"
    Keeping it short keeps CLI/debug output readable while still unique enough.
    """
    return f"{run_id[:8]}-{episode_index:04d}-{uuid.uuid4().hex[:8]}"


def identity_dict(run_id: str, episode_id: str, episode_index: int) -> Dict[str, object]:
    """Small helper to bundle identity fields for logging.

    Additive-only: callers merge this into the top-level JSON object for a log line.
    """
    return {
        "run_id": str(run_id),
        "episode_id": str(episode_id),
        "episode_index": int(episode_index),
    }
