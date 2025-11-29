# sim4/runtime/history.py

from typing import Dict, List, Optional, Any


class HistoryBuffer:
    """
    Stores snapshots and/or diffs across ticks.

    Supports:
      - full snapshots
      - diffs (patches)
      - ring-buffer mode
      - indexed access
      - exportable episode logs

    This is Era IV core:
      EpisodeDebugger, Replay, StageEpisodeV2 builder.
    """

    def __init__(self, use_diffs=True, limit: Optional[int] = None):
        """
        Args:
            use_diffs: if True, store diffs instead of full snapshots
            limit: max number of entries (ring buffer).
        """
        self.use_diffs = use_diffs
        self.limit = limit

        self._full_snapshots: Dict[int, Dict[str, Any]] = {}
        self._diffs: Dict[int, Dict[str, Any]] = {}

        # Keep tick order for iteration / trimming
        self._ticks: List[int] = []

    # ------------------------------------------------------------
    # 1. RECORD SNAPSHOT OR DIFF
    # ------------------------------------------------------------
    def record_snapshot(self, tick: int, snapshot: Dict[str, Any]):
        """Store full snapshot."""
        self._full_snapshots[tick] = snapshot
        self._register_tick(tick)

    def record_diff(self, tick: int, patch: Dict[str, Any]):
        """Store diff."""
        self._diffs[tick] = patch
        self._register_tick(tick)

    def _register_tick(self, tick: int):
        self._ticks.append(tick)
        self._maybe_trim()

    # ------------------------------------------------------------
    # 2. RING BUFFER TRIM
    # ------------------------------------------------------------
    def _maybe_trim(self):
        if self.limit is None:
            return

        while len(self._ticks) > self.limit:
            oldest = self._ticks.pop(0)
            self._full_snapshots.pop(oldest, None)
            self._diffs.pop(oldest, None)

    # ------------------------------------------------------------
    # 3. RETRIEVAL
    # ------------------------------------------------------------
    def get_snapshot(self, tick: int):
        return self._full_snapshots.get(tick)

    def get_diff(self, tick: int):
        return self._diffs.get(tick)

    def ticks(self):
        return list(self._ticks)

    # ------------------------------------------------------------
    # 4. EPISODE EXPORT
    # ------------------------------------------------------------
    def export_episode(self) -> Dict[str, Any]:
        """
        Export as:
        {
            "full": { tick: snapshot },
            "diffs": { tick: patch }
        }
        """
        return {
            "full": self._full_snapshots.copy(),
            "diffs": self._diffs.copy(),
            "order": self._ticks.copy(),
        }

    # ------------------------------------------------------------
    # 5. EPISODE IMPORT
    # ------------------------------------------------------------
    def load_episode(self, episode: Dict[str, Any]):
        self._full_snapshots = episode.get("full", {})
        self._diffs = episode.get("diffs", {})
        self._ticks = episode.get("order", [])
