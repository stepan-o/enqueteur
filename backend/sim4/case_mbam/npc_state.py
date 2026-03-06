from __future__ import annotations

"""Canonical runtime NPCState model + MBAM bootstrap defaults.

This module links persistent cast identity (CastRegistry) to runtime semantic
state for the fixed MBAM recurring cast.
"""

from dataclasses import dataclass
from typing import Literal

from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import MbamRoomId

from .cast_registry import FixedCastId, get_cast_entry, list_cast_ids


NpcAvailability = Literal["available", "busy", "gone", "restricted"]
NpcStance = Literal["helpful", "procedural", "evasive", "defensive", "manipulative", "flustered"]
NpcEmotion = Literal["calm", "stressed", "amused", "annoyed", "nervous", "guarded"]
NpcSoftAlignmentHint = Literal[
    "protecting_institution",
    "protecting_self",
    "protecting_someone_else",
    "saving_face",
    "helping_quietly",
]
NpcInteractionMode = Literal["direct", "gentle", "formal", "procedural", "pressure", "reassure"]
NpcTrustTrend = Literal["up", "flat", "down"]


@dataclass(frozen=True)
class NPCScheduleState:
    current_beat_id: str | None
    next_beat_id: str | None
    last_transition_at: str | None


@dataclass(frozen=True)
class NPCCardState:
    portrait_variant: str
    tell_cue: str | None
    suggested_interaction_mode: NpcInteractionMode
    trust_trend: NpcTrustTrend


@dataclass(frozen=True)
class NPCState:
    npc_id: FixedCastId
    current_room_id: str
    availability: NpcAvailability
    trust: float
    stress: float
    stance: NpcStance
    emotion: NpcEmotion
    soft_alignment_hint: NpcSoftAlignmentHint
    visible_behavior_flags: tuple[str, ...]
    known_fact_flags: tuple[str, ...]
    belief_flags: tuple[str, ...]
    hidden_flags: tuple[str, ...]
    misremember_flags: tuple[str, ...]
    current_scene_id: str | None
    schedule_state: NPCScheduleState
    card_state: NPCCardState

    def __post_init__(self) -> None:
        if not self.current_room_id:
            raise ValueError("NPCState.current_room_id must be non-empty")
        if self.trust < 0:
            raise ValueError("NPCState.trust must be >= 0")
        if self.stress < 0:
            raise ValueError("NPCState.stress must be >= 0")


_ROOM_TOKEN_TO_WORLD_ID: dict[str, int] = {
    "MBAM_LOBBY": int(MbamRoomId.MBAM_LOBBY),
    "GALLERY_AFFICHES": int(MbamRoomId.GALLERY_AFFICHES),
    "SECURITY_OFFICE": int(MbamRoomId.SECURITY_OFFICE),
    "SERVICE_CORRIDOR": int(MbamRoomId.SERVICE_CORRIDOR),
    "CAFE_DE_LA_RUE": int(MbamRoomId.CAFE_DE_LA_RUE),
}

_DEFAULT_ROOM_BY_NPC: dict[FixedCastId, str] = {
    "elodie": "MBAM_LOBBY",
    "marc": "SECURITY_OFFICE",
    "samira": "GALLERY_AFFICHES",
    "laurent": "CAFE_DE_LA_RUE",
    "jo": "CAFE_DE_LA_RUE",
}

_DEFAULT_NEXT_BEAT_BY_NPC: dict[FixedCastId, str] = {
    "elodie": "T_PLUS_02_CURATOR_CONTAINMENT",
    "marc": "T_PLUS_05_GUARD_PATROL_SHIFT",
    "samira": "T_PLUS_08_INTERN_MOVEMENT",
    "laurent": "T_PLUS_10_DONOR_EVENT",
    "jo": "T_PLUS_12_BARISTA_WITNESS_WINDOW",
}

_DEFAULT_STANCE_BY_NPC: dict[FixedCastId, NpcStance] = {
    "elodie": "helpful",
    "marc": "procedural",
    "samira": "flustered",
    "laurent": "defensive",
    "jo": "helpful",
}

_DEFAULT_EMOTION_BY_NPC: dict[FixedCastId, NpcEmotion] = {
    "elodie": "guarded",
    "marc": "guarded",
    "samira": "nervous",
    "laurent": "guarded",
    "jo": "calm",
}

_DEFAULT_ALIGNMENT_BY_NPC: dict[FixedCastId, NpcSoftAlignmentHint] = {
    "elodie": "protecting_institution",
    "marc": "protecting_institution",
    "samira": "protecting_self",
    "laurent": "saving_face",
    "jo": "helping_quietly",
}

_DEFAULT_INTERACTION_BY_NPC: dict[FixedCastId, NpcInteractionMode] = {
    "elodie": "formal",
    "marc": "procedural",
    "samira": "reassure",
    "laurent": "formal",
    "jo": "gentle",
}

_DEFAULT_PORTRAIT_VARIANT_BY_NPC: dict[FixedCastId, str] = {
    "elodie": "calm",
    "marc": "procedural",
    "samira": "nervous",
    "laurent": "guarded",
    "jo": "relaxed",
}


def _ensure_world_room_presence(world_ctx: WorldContext) -> None:
    missing_tokens = [
        token
        for token, world_room_id in _ROOM_TOKEN_TO_WORLD_ID.items()
        if world_room_id not in world_ctx.rooms_by_id
    ]
    if missing_tokens:
        raise ValueError(
            "WorldContext is missing MBAM room ids required for NPCState bootstrap: "
            + ", ".join(sorted(missing_tokens))
        )


def build_initial_npc_state(*, npc_id: FixedCastId, world_ctx: WorldContext) -> NPCState:
    """Build deterministic initial runtime NPCState for one MBAM cast member."""
    _ensure_world_room_presence(world_ctx)
    entry = get_cast_entry(npc_id)
    room_token = _DEFAULT_ROOM_BY_NPC[npc_id]
    tell_cue = entry.tell_profile[0] if entry.tell_profile else None

    return NPCState(
        npc_id=npc_id,
        current_room_id=room_token,
        availability="available",
        trust=0.0,
        stress=0.0,
        stance=_DEFAULT_STANCE_BY_NPC[npc_id],
        emotion=_DEFAULT_EMOTION_BY_NPC[npc_id],
        soft_alignment_hint=_DEFAULT_ALIGNMENT_BY_NPC[npc_id],
        visible_behavior_flags=(f"tell_{tell_cue}" if tell_cue else "tell_none",),
        known_fact_flags=(),
        belief_flags=(),
        hidden_flags=("baseline_identity_loaded",),
        misremember_flags=(),
        current_scene_id=None,
        schedule_state=NPCScheduleState(
            current_beat_id=None,
            next_beat_id=_DEFAULT_NEXT_BEAT_BY_NPC[npc_id],
            last_transition_at=None,
        ),
        card_state=NPCCardState(
            portrait_variant=_DEFAULT_PORTRAIT_VARIANT_BY_NPC[npc_id],
            tell_cue=tell_cue,
            suggested_interaction_mode=_DEFAULT_INTERACTION_BY_NPC[npc_id],
            trust_trend="flat",
        ),
    )


def initialize_mbam_npc_states(world_ctx: WorldContext) -> dict[FixedCastId, NPCState]:
    """Initialize deterministic runtime NPCState map for the fixed MBAM cast."""
    _ensure_world_room_presence(world_ctx)
    return {
        npc_id: build_initial_npc_state(npc_id=npc_id, world_ctx=world_ctx)
        for npc_id in list_cast_ids()
    }


def resolve_world_room_id(room_token: str) -> int:
    """Map canonical MBAM room token to world room id."""
    if room_token not in _ROOM_TOKEN_TO_WORLD_ID:
        expected = ", ".join(sorted(_ROOM_TOKEN_TO_WORLD_ID.keys()))
        raise KeyError(f"Unknown MBAM room token: {room_token!r}; expected one of {expected}")
    return _ROOM_TOKEN_TO_WORLD_ID[room_token]


__all__ = [
    "NpcAvailability",
    "NpcStance",
    "NpcEmotion",
    "NpcSoftAlignmentHint",
    "NpcInteractionMode",
    "NpcTrustTrend",
    "NPCScheduleState",
    "NPCCardState",
    "NPCState",
    "build_initial_npc_state",
    "initialize_mbam_npc_states",
    "resolve_world_room_id",
]
