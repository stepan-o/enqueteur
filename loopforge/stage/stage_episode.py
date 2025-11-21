from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Mapping, Any

# Stage layer is UI-agnostic. These models are JSON-serializable containers that
# future stages (views, APIs) can consume. Field names are intended to be stable
# and forward-compatible. Keep them simple; avoid computed properties here.
#
# Chaos Goblins Clause: whimsical comments welcome; shapes must remain stable.


@dataclass
class StageAgentTraits:
    """Optional snapshot of agent traits for episode-level summaries.

    This is intentionally sparse in Sprint 0.1 — future sprints may expand it.
    Values are clamped/normalized upstream; here we just carry the snapshot.
    """

    risk_aversion: Optional[float] = None
    obedience: Optional[float] = None
    guardrail_reliance: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class StageNarrativeBlock:
    """Narrative atoms attached to days/agents. Pure text + light metadata.

    For Sprint 0.1 these will usually be empty lists; wiring only.
    """

    block_id: Optional[str] = None
    kind: str = "narrative"  # e.g., "recap", "beat", "aside"
    text: str = ""
    day_index: Optional[int] = None
    agent_name: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StageAgentDayView:
    """One agent's daily view in the stage layer.

    Keep this decoupled from analytics internals; copy only necessary fields.
    """

    name: str
    role: str
    avg_stress: float = 0.0
    guardrail_count: int = 0
    context_count: int = 0
    # Optional emotional read if available (mood/certainty/energy)
    emotional_read: Optional[Mapping[str, Any]] = None
    # Optional attribution cause ("random" | "system" | "self" | "supervisor"), if available
    attribution_cause: Optional[str] = None
    # Room for narrative snippets tied to this agent/day
    narrative: List[StageNarrativeBlock] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "avg_stress": self.avg_stress,
            "guardrail_count": self.guardrail_count,
            "context_count": self.context_count,
            "emotional_read": dict(self.emotional_read) if isinstance(self.emotional_read, dict) else (self.emotional_read if self.emotional_read is None else None),
            "attribution_cause": self.attribution_cause,
            "narrative": [n.to_dict() for n in self.narrative],
        }


@dataclass
class StageDay:
    day_index: int
    perception_mode: str
    tension_score: float
    agents: Dict[str, StageAgentDayView] = field(default_factory=dict)
    total_incidents: int = 0
    supervisor_activity: float = 0.0
    narrative: List[StageNarrativeBlock] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "day_index": self.day_index,
            "perception_mode": self.perception_mode,
            "tension_score": self.tension_score,
            "agents": {k: v.to_dict() for k, v in self.agents.items()},
            "total_incidents": self.total_incidents,
            "supervisor_activity": self.supervisor_activity,
            "narrative": [n.to_dict() for n in self.narrative],
        }


@dataclass
class StageAgentSummary:
    name: str
    role: str
    guardrail_total: int = 0
    context_total: int = 0
    stress_start: Optional[float] = None
    stress_end: Optional[float] = None
    trait_snapshot: Optional[StageAgentTraits] = None
    visual: str = ""
    vibe: str = ""
    tagline: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "guardrail_total": self.guardrail_total,
            "context_total": self.context_total,
            "stress_start": self.stress_start,
            "stress_end": self.stress_end,
            "trait_snapshot": self.trait_snapshot.to_dict() if self.trait_snapshot else None,
            "visual": self.visual,
            "vibe": self.vibe,
            "tagline": self.tagline,
        }


@dataclass
class StageEpisode:
    """Top-level Stage container for an episode.

    This object is stable and JSON-serializable. It mirrors the analytics
    summary shapes but stays decoupled from their internal implementations.
    """

    episode_id: Optional[str]
    run_id: Optional[str]
    episode_index: int

    # Episode-level analytics overlays
    tension_trend: List[float] = field(default_factory=list)

    days: List[StageDay] = field(default_factory=list)
    agents: Dict[str, StageAgentSummary] = field(default_factory=dict)

    # Optional narrative/story overlays
    story_arc: Optional[Mapping[str, Any]] = None  # stored as a plain dict
    narrative: List[StageNarrativeBlock] = field(default_factory=list)

    # Optional slow character memory snapshot
    long_memory: Optional[Dict[str, Mapping[str, Any]]] = None  # dict form

    # For convenience/testing: copy of the character registry slice used
    character_defs: Optional[Dict[str, Mapping[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "run_id": self.run_id,
            "episode_index": self.episode_index,
            "tension_trend": list(self.tension_trend),
            "days": [d.to_dict() for d in self.days],
            "agents": {k: v.to_dict() for k, v in self.agents.items()},
            "story_arc": dict(self.story_arc) if self.story_arc else None,
            "narrative": [n.to_dict() for n in self.narrative],
            "long_memory": {k: dict(v) for k, v in self.long_memory.items()} if self.long_memory else None,
            "character_defs": {k: dict(v) for k, v in self.character_defs.items()} if self.character_defs else None,
        }
