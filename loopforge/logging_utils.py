from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional, Iterable, List

from loopforge.types import (
    ActionLogEntry,
    AgentPerception,
    AgentActionPlan,
    ReflectionLogEntry,
    AgentReflection,
    SupervisorMessage,
    EpisodeTensionSnapshot,
)
from loopforge.ids import identity_dict


class JsonlActionLogger:
    """
    Minimal JSONL logger for action steps.

    Writes one JSON object per line. This is deliberately simple so it
    can be swapped out later.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def write_entry(self, entry: ActionLogEntry) -> None:
        line = json.dumps(entry.to_dict(), separators=(",", ":"))
        with self._path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.write("\n")

    def write_dict(self, data: Dict[str, Any]) -> None:
        """Write a pre-built dict as one JSON line.
        Additive convenience so callers can merge extra fields without
        modifying ActionLogEntry schemas.
        """
        line = json.dumps(data, separators=(",", ":"))
        with self._path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.write("\n")


def log_action_step(
    logger: JsonlActionLogger,
    perception: AgentPerception,
    plan: AgentActionPlan,
    action: Dict[str, Any],
    outcome: Optional[str] = None,
    *,
    episode_index: Optional[int] = None,
    day_index: Optional[int] = None,
    run_id: Optional[str] = None,
    episode_id: Optional[str] = None,
) -> None:
    entry = ActionLogEntry(
        step=perception.step,
        agent_name=perception.name,
        role=perception.role,
        mode=plan.mode,
        intent=plan.intent,
        move_to=plan.move_to,
        targets=list(plan.targets),
        riskiness=plan.riskiness,
        narrative=plan.narrative,
        outcome=outcome,
        raw_action=dict(action),
        perception=perception.to_dict(),
        episode_index=episode_index,
        day_index=day_index,
    )
    # Build base dict and add identity fields additively (no schema changes)
    data = entry.to_dict()
    try:
        # Prefer explicitly provided episode_index; otherwise use entry's value
        idx = entry.episode_index if episode_index is None else episode_index
        if run_id is not None or episode_id is not None:
            # Merge only provided pieces; ensure episode_index included from idx
            if run_id is not None and episode_id is not None and idx is not None:
                data.update(identity_dict(str(run_id), str(episode_id), int(idx)))
            else:
                if run_id is not None:
                    data["run_id"] = str(run_id)
                if episode_id is not None:
                    data["episode_id"] = str(episode_id)
                if idx is not None:
                    data["episode_index"] = int(idx)
    except Exception:
        # identity merge must not break logging
        pass
    # Logging must not crash the sim; swallow exceptions.
    try:
        # Use write_dict to preserve any additive fields
        logger.write_dict(data)
    except Exception:
        # Optional debug hook; for now, fail-soft.
        pass


def read_action_log_entries(path: Path) -> List[ActionLogEntry]:
    """Read a JSONL file of action entries.

    Fail-soft: if the file doesn't exist, return an empty list. Any
    malformed lines are skipped.
    """
    p = Path(path)
    if not p.exists():
        return []
    entries: List[ActionLogEntry] = []
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entries.append(ActionLogEntry.from_dict(data))
                except Exception:
                    # skip malformed lines
                    continue
    except Exception:
        # If the file becomes unreadable, return what we have so far
        return entries
    return entries


def read_action_log_entries_for_episode(path: Path, run_id: str, episode_id: str) -> List[dict]:
    """Read JSONL and return only dict rows matching run_id AND episode_id.

    - Lines missing these keys or with non-matching values are ignored.
    - Fail-soft on malformed lines (skip), same as existing readers.
    - Returns raw dicts so callers can construct strong types as needed.
    """
    p = Path(path)
    if not p.exists():
        return []
    out: List[dict] = []
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue
                try:
                    if isinstance(data, dict) and data.get("run_id") == run_id and data.get("episode_id") == episode_id:
                        out.append(data)
                except Exception:
                    # Any unexpected shapes are ignored
                    continue
    except Exception:
        return out
    return out


class JsonlReflectionLogger:
    """Minimal JSONL logger for daily reflections."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_reflection(
        self,
        agent_name: str,
        role: str,
        day_index: int,
        reflection: AgentReflection,
        traits_after: Dict[str, float],
        *,
        episode_index: Optional[int] = None,
    ) -> None:
        entry = ReflectionLogEntry(
            agent_name=agent_name,
            role=role,
            day_index=day_index,
            reflection=reflection,
            traits_after=traits_after,
            perception_mode=getattr(reflection, "perception_mode", None),
            supervisor_perceived_intent=getattr(reflection, "supervisor_perceived_intent", None),
            episode_index=episode_index,
        )
        with self.path.open("a", encoding="utf8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")


class JsonlSupervisorLogger:
    """
    Minimal JSONL logger for Supervisor messages.
    One JSON object per line, using SupervisorMessage.to_dict().
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_message(self, message: SupervisorMessage) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(message.to_dict()))
            f.write("\n")


class JsonlWeaveLogger:
    """
    JSONL writer for episode weave snapshots.

    Writes one EpisodeTensionSnapshot per line via snapshot.to_dict().
    Fail-soft: I/O issues are swallowed to avoid impacting callers.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            # fail-soft on directory creation
            pass

    def write_snapshot(self, snapshot: EpisodeTensionSnapshot) -> None:
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(snapshot.to_dict()))
                f.write("\n")
        except Exception:
            # fail-soft
            pass
