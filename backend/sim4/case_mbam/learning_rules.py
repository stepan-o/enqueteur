from __future__ import annotations

"""Deterministic MBAM learning grading + difficulty rules (Phase 6D).

This module is intentionally narrow and MBAM-specific.
It centralizes difficulty-aware learning semantics so:
- dialogue summary grading
- learning projection policy
remain consistent and replay-safe.
"""

from typing import Literal

from .models import DifficultyProfile, SceneId


PromptGenerosity = Literal["high", "medium"]
ConfirmationStrength = Literal["explicit", "compact"]
SummaryStrictness = Literal["relaxed", "strict"]
LanguageSupportLevel = Literal["fr_plus_meta", "fr_primary"]


_D1_REQUIRED_SUMMARY_KEY_FACTS: dict[SceneId, tuple[str, ...]] = {
    "S1": ("N1",),
    "S2": ("N2",),
    "S3": ("N3",),
    "S4": ("N4",),
    "S5": ("N8",),
}


def difficulty_base_hint_rank(difficulty: DifficultyProfile) -> int:
    # D0 starts one step more generous than D1.
    if difficulty == "D0":
        return 1
    return 0


def difficulty_max_hint_rank(difficulty: DifficultyProfile) -> int:
    # D1 avoids english-meta tier; D0 can escalate fully.
    if difficulty == "D0":
        return 3
    return 2


def difficulty_prompt_generosity(difficulty: DifficultyProfile) -> PromptGenerosity:
    if difficulty == "D0":
        return "high"
    return "medium"


def difficulty_confirmation_strength(difficulty: DifficultyProfile) -> ConfirmationStrength:
    if difficulty == "D0":
        return "explicit"
    return "compact"


def difficulty_summary_strictness(difficulty: DifficultyProfile) -> SummaryStrictness:
    if difficulty == "D0":
        return "relaxed"
    return "strict"


def difficulty_language_support_level(difficulty: DifficultyProfile) -> LanguageSupportLevel:
    if difficulty == "D0":
        return "fr_plus_meta"
    return "fr_primary"


def effective_summary_min_fact_count(
    *,
    difficulty: DifficultyProfile,
    scene_id: SceneId,
    base_min_fact_count: int,
) -> int:
    # Keep relaxation narrow to preserve case solvability/structure.
    if difficulty == "D0" and scene_id == "S5" and base_min_fact_count > 1:
        return base_min_fact_count - 1
    return base_min_fact_count


def required_summary_key_fact_ids(
    *,
    difficulty: DifficultyProfile,
    scene_id: SceneId,
) -> tuple[str, ...]:
    if difficulty == "D1":
        return _D1_REQUIRED_SUMMARY_KEY_FACTS.get(scene_id, ())
    return ()


__all__ = [
    "ConfirmationStrength",
    "LanguageSupportLevel",
    "PromptGenerosity",
    "SummaryStrictness",
    "difficulty_base_hint_rank",
    "difficulty_confirmation_strength",
    "difficulty_language_support_level",
    "difficulty_max_hint_rank",
    "difficulty_prompt_generosity",
    "difficulty_summary_strictness",
    "effective_summary_min_fact_count",
    "required_summary_key_fact_ids",
]

