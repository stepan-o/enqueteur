from __future__ import annotations

"""
Deterministic Supervisor Activity computation (Sprint 4).

- Pure helper that computes a per-day scalar in [0,1]
- Read-only; does not change simulation behavior
- Intended to be used by the CLI wiring to pass into summarize_day(...)
"""

from typing import List

from .types import ActionLogEntry


def compute_supervisor_activity(
    supervisor_entries_for_day: List[ActionLogEntry],
    steps_per_day: int,
) -> float:
    """
    Deterministic fraction of steps with supervisor activity, clamped to [0,1].
    If steps_per_day <= 0, returns 0.0.
    """
    try:
        n_steps = int(steps_per_day)
    except Exception:
        n_steps = 0
    if n_steps <= 0:
        return 0.0

    try:
        n = len(supervisor_entries_for_day) if supervisor_entries_for_day is not None else 0
    except Exception:
        n = 0
    raw = float(n) / float(n_steps)
    if raw < 0.0:
        return 0.0
    if raw > 1.0:
        return 1.0
    return raw
