from __future__ import annotations

"""Deterministic MBAM learning-state + scaffolding policy substrate (Phase 6A).

This module is intentionally narrow and MBAM-scoped:
- tracks learner-facing summary/minigame progression state
- derives deterministic scaffolding policy from difficulty + scene/turn state
- does not execute minigame UI, dialogue UI, or LLM behavior
"""

from dataclasses import dataclass
from typing import Literal

from .dialogue_runtime import DialogueSceneRuntimeState, DialogueTurnLogEntry
from .investigation_progress import InvestigationProgressState
from .models import CaseState, DifficultyProfile, SceneId


LearningHintLevel = Literal[
    "soft_hint",
    "sentence_stem",
    "rephrase_choice",
    "english_meta_help",
]

MinigameId = Literal[
    "MG1_LABEL_READING",
    "MG2_BADGE_LOG",
    "MG3_RECEIPT_READING",
    "MG4_TORN_NOTE_RECONSTRUCTION",
]


@dataclass(frozen=True)
class SceneSummaryLearningState:
    scene_id: SceneId
    required: bool
    min_fact_count: int
    attempt_count: int
    completed: bool
    summary_passed: bool | None
    last_summary_code: str | None

    def __post_init__(self) -> None:
        if self.min_fact_count < 0:
            raise ValueError("SceneSummaryLearningState.min_fact_count must be >= 0")
        if self.attempt_count < 0:
            raise ValueError("SceneSummaryLearningState.attempt_count must be >= 0")


@dataclass(frozen=True)
class MinigameLearningState:
    minigame_id: MinigameId
    attempt_count: int
    completed: bool
    score: int
    max_score: int
    status: Literal["not_started", "in_progress", "completed"]

    def __post_init__(self) -> None:
        if self.attempt_count < 0:
            raise ValueError("MinigameLearningState.attempt_count must be >= 0")
        if self.max_score < 0:
            raise ValueError("MinigameLearningState.max_score must be >= 0")
        if self.score < 0 or self.score > self.max_score:
            raise ValueError("MinigameLearningState.score must be in [0, max_score]")


@dataclass(frozen=True)
class ScaffoldingPolicyState:
    scene_id: SceneId | None
    current_hint_level: LearningHintLevel
    current_hint_rank: int
    allowed_hint_levels: tuple[LearningHintLevel, ...]
    recommended_mode: LearningHintLevel
    english_meta_allowed: bool
    french_action_required: bool
    reason_code: str
    soft_hint_key: str | None
    sentence_stem_key: str | None
    rephrase_set_id: str | None
    english_meta_key: str | None
    target_minigame_id: MinigameId | None = None

    def __post_init__(self) -> None:
        if self.current_hint_rank < 0:
            raise ValueError("ScaffoldingPolicyState.current_hint_rank must be >= 0")


@dataclass(frozen=True)
class LearningState:
    difficulty_profile: DifficultyProfile
    active_scene_id: SceneId | None
    current_hint_level: LearningHintLevel
    summary_by_scene: tuple[SceneSummaryLearningState, ...]
    minigames: tuple[MinigameLearningState, ...]
    scaffolding_policy: ScaffoldingPolicyState


_SCENE_ORDER: tuple[SceneId, ...] = ("S1", "S2", "S3", "S4", "S5")
_LEVELS: tuple[LearningHintLevel, ...] = (
    "soft_hint",
    "sentence_stem",
    "rephrase_choice",
    "english_meta_help",
)
_SCENE_TO_HINT_KEYS: dict[SceneId, tuple[str, str, str, str, MinigameId | None]] = {
    "S1": (
        "hint:s1_incident_scope",
        "stem:s1_polite_incident",
        "rephrase:s1_incident_core",
        "meta:s1_english_prompting",
        "MG1_LABEL_READING",
    ),
    "S2": (
        "hint:s2_security_protocol",
        "stem:s2_access_request",
        "rephrase:s2_access_reason",
        "meta:s2_english_polite_security",
        "MG2_BADGE_LOG",
    ),
    "S3": (
        "hint:s3_timeline_anchor",
        "stem:s3_time_sequence",
        "rephrase:s3_timeline_checks",
        "meta:s3_english_timeline_frame",
        "MG4_TORN_NOTE_RECONSTRUCTION",
    ),
    "S4": (
        "hint:s4_cafe_witness_window",
        "stem:s4_witness_prompt",
        "rephrase:s4_clothing_timestamp",
        "meta:s4_english_witness_focus",
        "MG3_RECEIPT_READING",
    ),
    "S5": (
        "hint:s5_corroboration_requirements",
        "stem:s5_confrontation_structure",
        "rephrase:s5_accusation_logic",
        "meta:s5_english_reasoning_frame",
        None,
    ),
}


def _mg_status(*, attempt_count: int, completed: bool) -> Literal["not_started", "in_progress", "completed"]:
    if completed:
        return "completed"
    if attempt_count > 0:
        return "in_progress"
    return "not_started"


def _has_observation(progress: InvestigationProgressState, object_id: str, affordance_id: str) -> bool:
    needle = f"obs:{object_id}:{affordance_id}"
    return needle in set(progress.observed_clue_ids)


def _build_minigame_states(progress: InvestigationProgressState) -> tuple[MinigameLearningState, ...]:
    known_facts = set(progress.known_fact_ids)
    discovered = set(progress.discovered_evidence_ids).union(progress.collected_evidence_ids)

    mg1_attempt = 1 if _has_observation(progress, "O3_WALL_LABEL", "read") else 0
    mg1_completed = mg1_attempt > 0
    mg1_score = 2 if mg1_completed else 0

    mg2_attempt = 1 if _has_observation(progress, "O6_BADGE_TERMINAL", "view_logs") else 0
    mg2_completed = mg2_attempt > 0 and "N3" in known_facts
    mg2_score = 2 if mg2_completed else (1 if mg2_attempt else 0)

    mg3_attempt = 1 if _has_observation(progress, "O9_RECEIPT_PRINTER", "read_receipt") else 0
    mg3_completed = mg3_attempt > 0 and "N4" in known_facts
    mg3_score = 2 if mg3_completed else (1 if mg3_attempt else 0)

    mg4_attempt = 1 if ("E1_TORN_NOTE" in discovered or _has_observation(progress, "O4_BENCH", "inspect")) else 0
    mg4_completed = "N6" in known_facts
    mg4_score = 3 if mg4_completed else (1 if mg4_attempt else 0)

    return (
        MinigameLearningState(
            minigame_id="MG1_LABEL_READING",
            attempt_count=mg1_attempt,
            completed=mg1_completed,
            score=mg1_score,
            max_score=2,
            status=_mg_status(attempt_count=mg1_attempt, completed=mg1_completed),
        ),
        MinigameLearningState(
            minigame_id="MG2_BADGE_LOG",
            attempt_count=mg2_attempt,
            completed=mg2_completed,
            score=mg2_score,
            max_score=2,
            status=_mg_status(attempt_count=mg2_attempt, completed=mg2_completed),
        ),
        MinigameLearningState(
            minigame_id="MG3_RECEIPT_READING",
            attempt_count=mg3_attempt,
            completed=mg3_completed,
            score=mg3_score,
            max_score=2,
            status=_mg_status(attempt_count=mg3_attempt, completed=mg3_completed),
        ),
        MinigameLearningState(
            minigame_id="MG4_TORN_NOTE_RECONSTRUCTION",
            attempt_count=mg4_attempt,
            completed=mg4_completed,
            score=mg4_score,
            max_score=3,
            status=_mg_status(attempt_count=mg4_attempt, completed=mg4_completed),
        ),
    )


def _summary_state_for_scene(
    scene_id: SceneId,
    runtime_state: DialogueSceneRuntimeState,
    recent_turns: tuple[DialogueTurnLogEntry, ...],
) -> SceneSummaryLearningState:
    scene_def = getattr(runtime_state.scene_definitions, scene_id).scene_state
    completion_map = {sid: completion for sid, completion in runtime_state.scene_completion_states}
    completion_state = completion_map[scene_id]

    attempts = 0
    last_code: str | None = None
    for row in recent_turns:
        if row.scene_id != scene_id:
            continue
        if row.intent_id == "summarize_understanding" or row.summary_check_code is not None:
            attempts += 1
        if row.summary_check_code is not None:
            last_code = row.summary_check_code
    summary_passed = None
    if last_code is not None:
        summary_passed = last_code == "summary_passed"

    return SceneSummaryLearningState(
        scene_id=scene_id,
        required=scene_def.summary_requirement.required,
        min_fact_count=scene_def.summary_requirement.min_fact_count,
        attempt_count=attempts,
        completed=completion_state == "completed",
        summary_passed=summary_passed,
        last_summary_code=last_code,
    )


def _base_rank_for_difficulty(difficulty_profile: DifficultyProfile) -> int:
    if difficulty_profile == "D0":
        return 0
    return 0


def _max_rank_for_difficulty(difficulty_profile: DifficultyProfile) -> int:
    if difficulty_profile == "D0":
        return 3
    return 2


def _level_for_rank(rank: int) -> LearningHintLevel:
    clamped = max(0, min(rank, len(_LEVELS) - 1))
    return _LEVELS[clamped]


def _build_scaffolding_policy(
    *,
    case_state: CaseState,
    runtime_state: DialogueSceneRuntimeState,
    recent_turns: tuple[DialogueTurnLogEntry, ...],
) -> ScaffoldingPolicyState:
    scene_id = runtime_state.active_scene_id
    base_rank = _base_rank_for_difficulty(case_state.difficulty_profile)
    max_rank = _max_rank_for_difficulty(case_state.difficulty_profile)

    if scene_id is None:
        level = _level_for_rank(base_rank)
        allowed = tuple(_LEVELS[: base_rank + 1])
        return ScaffoldingPolicyState(
            scene_id=None,
            current_hint_level=level,
            current_hint_rank=base_rank,
            allowed_hint_levels=allowed,
            recommended_mode=level,
            english_meta_allowed="english_meta_help" in set(allowed),
            french_action_required=True,
            reason_code="no_active_scene",
            soft_hint_key=None,
            sentence_stem_key=None,
            rephrase_set_id=None,
            english_meta_key=None,
            target_minigame_id=None,
        )

    scene_turns = tuple(row for row in recent_turns if row.scene_id == scene_id)
    consecutive_non_accept = 0
    for row in reversed(scene_turns):
        if row.status == "accepted":
            break
        if row.status in {"repair", "refused", "blocked_gate"}:
            consecutive_non_accept += 1
    recent_summary_pressure = 0
    if scene_turns:
        latest_summary = next((row.summary_check_code for row in reversed(scene_turns) if row.summary_check_code), None)
        if latest_summary in {"summary_required", "summary_needed", "summary_insufficient_facts"}:
            recent_summary_pressure = 1

    rank = min(max_rank, base_rank + consecutive_non_accept + recent_summary_pressure)
    level = _level_for_rank(rank)
    allowed = tuple(_LEVELS[: rank + 1])
    hint_key, stem_key, rephrase_key, meta_key, target_mg = _SCENE_TO_HINT_KEYS[scene_id]

    english_meta_allowed = "english_meta_help" in set(allowed)
    if not english_meta_allowed:
        meta_key = None

    reason = "baseline_scene_support"
    if consecutive_non_accept > 0:
        reason = "escalated_after_repairs"
    elif recent_summary_pressure > 0:
        reason = "summary_pressure_escalation"

    return ScaffoldingPolicyState(
        scene_id=scene_id,
        current_hint_level=level,
        current_hint_rank=rank,
        allowed_hint_levels=allowed,
        recommended_mode=level,
        english_meta_allowed=english_meta_allowed,
        french_action_required=True,
        reason_code=reason,
        soft_hint_key=hint_key if "soft_hint" in set(allowed) else None,
        sentence_stem_key=stem_key if "sentence_stem" in set(allowed) else None,
        rephrase_set_id=rephrase_key if "rephrase_choice" in set(allowed) else None,
        english_meta_key=meta_key,
        target_minigame_id=target_mg,
    )


def build_learning_state(
    *,
    case_state: CaseState,
    runtime_state: DialogueSceneRuntimeState,
    progress: InvestigationProgressState,
    recent_turns: tuple[DialogueTurnLogEntry, ...] = (),
) -> LearningState:
    summary_by_scene = tuple(
        _summary_state_for_scene(scene_id, runtime_state, recent_turns) for scene_id in _SCENE_ORDER
    )
    minigames = _build_minigame_states(progress)
    policy = _build_scaffolding_policy(
        case_state=case_state,
        runtime_state=runtime_state,
        recent_turns=recent_turns,
    )
    return LearningState(
        difficulty_profile=case_state.difficulty_profile,
        active_scene_id=runtime_state.active_scene_id,
        current_hint_level=policy.current_hint_level,
        summary_by_scene=summary_by_scene,
        minigames=minigames,
        scaffolding_policy=policy,
    )


def build_visible_learning_projection(
    *,
    case_state: CaseState,
    runtime_state: DialogueSceneRuntimeState,
    progress: InvestigationProgressState,
    recent_turns: tuple[DialogueTurnLogEntry, ...] = (),
) -> dict[str, object]:
    state = build_learning_state(
        case_state=case_state,
        runtime_state=runtime_state,
        progress=progress,
        recent_turns=recent_turns,
    )
    return {
        "difficulty_profile": state.difficulty_profile,
        "active_scene_id": state.active_scene_id,
        "current_hint_level": state.current_hint_level,
        "summary_by_scene": [
            {
                "scene_id": row.scene_id,
                "required": row.required,
                "min_fact_count": row.min_fact_count,
                "attempt_count": row.attempt_count,
                "completed": row.completed,
                "summary_passed": row.summary_passed,
                "last_summary_code": row.last_summary_code,
            }
            for row in state.summary_by_scene
        ],
        "minigames": [
            {
                "minigame_id": row.minigame_id,
                "attempt_count": row.attempt_count,
                "completed": row.completed,
                "score": row.score,
                "max_score": row.max_score,
                "status": row.status,
            }
            for row in state.minigames
        ],
        "scaffolding_policy": {
            "scene_id": state.scaffolding_policy.scene_id,
            "current_hint_level": state.scaffolding_policy.current_hint_level,
            "current_hint_rank": state.scaffolding_policy.current_hint_rank,
            "allowed_hint_levels": list(state.scaffolding_policy.allowed_hint_levels),
            "recommended_mode": state.scaffolding_policy.recommended_mode,
            "english_meta_allowed": state.scaffolding_policy.english_meta_allowed,
            "french_action_required": state.scaffolding_policy.french_action_required,
            "reason_code": state.scaffolding_policy.reason_code,
            "soft_hint_key": state.scaffolding_policy.soft_hint_key,
            "sentence_stem_key": state.scaffolding_policy.sentence_stem_key,
            "rephrase_set_id": state.scaffolding_policy.rephrase_set_id,
            "english_meta_key": state.scaffolding_policy.english_meta_key,
            "target_minigame_id": state.scaffolding_policy.target_minigame_id,
        },
    }


def build_debug_learning_projection(
    *,
    case_state: CaseState,
    runtime_state: DialogueSceneRuntimeState,
    progress: InvestigationProgressState,
    recent_turns: tuple[DialogueTurnLogEntry, ...] = (),
) -> dict[str, object]:
    state = build_learning_state(
        case_state=case_state,
        runtime_state=runtime_state,
        progress=progress,
        recent_turns=recent_turns,
    )
    return {
        "case_id": case_state.case_id,
        "seed": case_state.seed,
        "difficulty_profile": case_state.difficulty_profile,
        "current_hint_level": state.current_hint_level,
        "scaffolding_policy": {
            "scene_id": state.scaffolding_policy.scene_id,
            "reason_code": state.scaffolding_policy.reason_code,
            "current_hint_rank": state.scaffolding_policy.current_hint_rank,
            "allowed_hint_levels": list(state.scaffolding_policy.allowed_hint_levels),
            "recommended_mode": state.scaffolding_policy.recommended_mode,
            "french_action_required": state.scaffolding_policy.french_action_required,
        },
        "summary_by_scene": [
            {
                "scene_id": row.scene_id,
                "required": row.required,
                "attempt_count": row.attempt_count,
                "summary_passed": row.summary_passed,
                "last_summary_code": row.last_summary_code,
                "completed": row.completed,
            }
            for row in state.summary_by_scene
        ],
        "minigames": [
            {
                "minigame_id": row.minigame_id,
                "attempt_count": row.attempt_count,
                "completed": row.completed,
                "score": row.score,
                "status": row.status,
            }
            for row in state.minigames
        ],
    }


__all__ = [
    "LearningHintLevel",
    "LearningState",
    "MinigameId",
    "MinigameLearningState",
    "ScaffoldingPolicyState",
    "SceneSummaryLearningState",
    "build_learning_state",
    "build_visible_learning_projection",
    "build_debug_learning_projection",
]
