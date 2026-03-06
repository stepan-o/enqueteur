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
from .models import CaseState, CharacterOverlay, Helpfulness


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
    profile_id: str | None
    suggested_interaction_mode: NpcInteractionMode
    trust_trend: NpcTrustTrend


@dataclass(frozen=True)
class NPCState:
    npc_id: FixedCastId
    overlay_role_slot: str
    overlay_helpfulness: Helpfulness
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

_HELPFULNESS_TO_TRUST: dict[Helpfulness, float] = {
    "none": 0.0,
    "low": 0.0,
    "medium": 0.1,
    "high": 0.2,
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


def _state_with_overlay(state: NPCState, overlay: CharacterOverlay) -> NPCState:
    role_slot = overlay.role_slot
    helpfulness = overlay.helpfulness

    stance: NpcStance
    if role_slot == "ALLY":
        stance = "helpful"
    elif role_slot == "MISDIRECTOR":
        stance = "manipulative"
    elif role_slot == "CULPRIT":
        stance = "defensive"
    elif helpfulness == "high":
        stance = "helpful"
    elif helpfulness == "low":
        stance = "evasive"
    else:
        stance = state.stance

    alignment: NpcSoftAlignmentHint
    if role_slot == "ALLY":
        alignment = "helping_quietly"
    elif role_slot == "MISDIRECTOR":
        alignment = "saving_face"
    elif role_slot == "CULPRIT":
        alignment = "protecting_self"
    else:
        alignment = state.soft_alignment_hint

    stress = 0.0
    if role_slot == "CULPRIT":
        stress = 0.25
    elif role_slot == "MISDIRECTOR":
        stress = 0.15
    elif helpfulness == "high":
        stress = 0.05

    visible_flags = tuple(
        sorted(
            {
                *state.visible_behavior_flags,
                f"overlay_role_{role_slot.lower()}",
                f"overlay_helpfulness_{helpfulness}",
            }
        )
    )
    hidden_flags = tuple(sorted({*state.hidden_flags, *overlay.hidden_flags}))

    return NPCState(
        npc_id=state.npc_id,
        overlay_role_slot=role_slot,
        overlay_helpfulness=helpfulness,
        current_room_id=state.current_room_id,
        availability=state.availability,
        trust=_HELPFULNESS_TO_TRUST[helpfulness],
        stress=stress,
        stance=stance,
        emotion=state.emotion,
        soft_alignment_hint=alignment,
        visible_behavior_flags=visible_flags,
        known_fact_flags=tuple(overlay.knowledge_flags),
        belief_flags=tuple(overlay.belief_flags),
        hidden_flags=hidden_flags,
        misremember_flags=tuple(overlay.misremember_flags),
        current_scene_id=state.current_scene_id,
        schedule_state=state.schedule_state,
        card_state=NPCCardState(
            portrait_variant=state.card_state.portrait_variant,
            tell_cue=state.card_state.tell_cue,
            profile_id=overlay.state_card_profile_id,
            suggested_interaction_mode=state.card_state.suggested_interaction_mode,
            trust_trend=state.card_state.trust_trend,
        ),
    )


def build_initial_npc_state(*, npc_id: FixedCastId, world_ctx: WorldContext) -> NPCState:
    """Build deterministic initial runtime NPCState for one MBAM cast member."""
    _ensure_world_room_presence(world_ctx)
    entry = get_cast_entry(npc_id)
    room_token = _DEFAULT_ROOM_BY_NPC[npc_id]
    tell_cue = entry.tell_profile[0] if entry.tell_profile else None

    return NPCState(
        npc_id=npc_id,
        overlay_role_slot=entry.identity_role.upper(),
        overlay_helpfulness="medium",
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
            profile_id=None,
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


def initialize_mbam_npc_states_from_case_state(
    world_ctx: WorldContext,
    case_state: CaseState,
) -> dict[FixedCastId, NPCState]:
    """Initialize MBAM NPC runtime state and apply deterministic CaseState overlays."""
    baseline = initialize_mbam_npc_states(world_ctx)
    return {
        "elodie": _state_with_overlay(baseline["elodie"], case_state.cast_overlay.elodie),
        "marc": _state_with_overlay(baseline["marc"], case_state.cast_overlay.marc),
        "samira": _state_with_overlay(baseline["samira"], case_state.cast_overlay.samira),
        "laurent": _state_with_overlay(baseline["laurent"], case_state.cast_overlay.laurent),
        "jo": _state_with_overlay(baseline["jo"], case_state.cast_overlay.jo),
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
    "initialize_mbam_npc_states_from_case_state",
    "resolve_world_room_id",
]
