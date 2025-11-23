from __future__ import annotations

"""
Identity helper utilities (Sprint 1 — Foundations only).

These helpers operate purely on append‑only JSONL logs and DO NOT change any
runtime behavior of the simulation, CLI, analysis, or API. They are intended to
support future sprints where identity discipline will be enforced.

Functions:
- detect_latest_episode_identity(action_log_path: Path) -> Optional[tuple[str, str, int]]
- verify_episode_identity_in_log(action_log_path: Path, run_id: str, episode_id: str, episode_index: int) -> bool

Fail‑soft philosophy:
- Missing files → return None/False.
- Malformed lines → skipped.
"""

from pathlib import Path
from typing import Optional, Tuple
import json


def _iter_jsonl_lines(path: Path):
    """Yield parsed JSON objects for each non-empty line; skip malformed.

    Fail-soft: if file missing or unreadable, yield nothing.
    """
    p = Path(path)
    if not p.exists():
        return
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except Exception:
        # unreadable file → behave as empty
        return


def detect_latest_episode_identity(action_log_path: Path) -> Optional[Tuple[str, str, int]]:
    """Return (run_id, episode_id, episode_index) for the most recent episode.

    Strategy:
    - Read the JSONL file; if missing → None.
    - Scan from the end (latest lines first) and find the first line that
      contains all of: run_id, episode_id, episode_index.
    - Return that tuple; if none found → None.

    Notes:
    - This approximates selecting the "last contiguous block" by choosing the
      identity of the last valid line; logs are append-only, so this reflects
      the latest identity-bearing episode block.
    - Malformed or non-dict lines are ignored.
    """
    p = Path(action_log_path)
    if not p.exists():
        return None
    try:
        # For simplicity and given test-scale files, load into memory and scan reverse.
        with p.open("r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        for line in reversed(lines):
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            run_id = obj.get("run_id")
            episode_id = obj.get("episode_id")
            episode_index = obj.get("episode_index")
            if run_id is None or episode_id is None or episode_index is None:
                continue
            try:
                return str(run_id), str(episode_id), int(episode_index)
            except Exception:
                # Non-coercible values → treat as invalid row
                continue
        return None
    except PermissionError:
        # Surface only truly unexpected permission errors per spec
        raise
    except Exception:
        # Other IO issues → fail-soft
        return None


def verify_episode_identity_in_log(
    action_log_path: Path,
    run_id: str,
    episode_id: str,
    episode_index: int,
) -> bool:
    """Return True if at least one log row matches the given identity.

    Fail-soft behavior:
    - Missing file → False
    - Malformed lines → skipped
    - Streaming read to keep memory bounded
    """
    p = Path(action_log_path)
    if not p.exists():
        return False
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue
                try:
                    if (
                        obj.get("run_id") == run_id
                        and obj.get("episode_id") == episode_id
                        and int(obj.get("episode_index", -1)) == int(episode_index)
                    ):
                        return True
                except Exception:
                    # Non-int episode_index or coercion error → treat as non-match
                    continue
        return False
    except Exception:
        # Any unexpected IO error → fail-soft to False
        return False


__all__ = [
    "detect_latest_episode_identity",
    "verify_episode_identity_in_log",
]
