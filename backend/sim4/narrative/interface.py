from __future__ import annotations

"""
Narrative engine interface (Sub‑Sprint 8.1).

Defines the runtime-facing NarrativeEngineInterface and a NullNarrativeEngine
stub implementation with no side effects and no external calls.

Layering:
- Import DTOs from backend.sim4.runtime only.
- No imports from ecs/, world/, snapshot/ directly (consumers import via runtime).
- No network, no I/O, no randomness.
"""

from dataclasses import dataclass

from backend.sim4.runtime import (
    NarrativeTickContext,
    NarrativeTickOutput,
    NarrativeEpisodeContext,
    NarrativeEpisodeOutput,
    NarrativeUICallContext,
    NarrativeUIText,
)


class NarrativeEngineInterface:
    def run_tick_jobs(self, ctx: NarrativeTickContext) -> NarrativeTickOutput:  # pragma: no cover - interface
        raise NotImplementedError

    def summarize_episode(self, ctx: NarrativeEpisodeContext) -> NarrativeEpisodeOutput:  # pragma: no cover - interface
        raise NotImplementedError

    def describe_scene(self, ctx: NarrativeUICallContext) -> NarrativeUIText:  # pragma: no cover - interface
        raise NotImplementedError


class NullNarrativeEngine(NarrativeEngineInterface):
    """
    Minimal stub engine for Sprint 8:
    - No LLM calls
    - No side effects
    """

    def run_tick_jobs(self, ctx: NarrativeTickContext) -> NarrativeTickOutput:
        return NarrativeTickOutput(
            substrate_suggestions=[],
            story_fragments=[],
            memory_updates=[],
        )

    def summarize_episode(self, ctx: NarrativeEpisodeContext) -> NarrativeEpisodeOutput:
        return NarrativeEpisodeOutput(
            summary_text="(narrative disabled)",
            character_summaries={},
            key_moments=[],
            memory_updates=[],
        )

    def describe_scene(self, ctx: NarrativeUICallContext) -> NarrativeUIText:
        return NarrativeUIText(text="(narrative disabled)")


__all__ = [
    "NarrativeEngineInterface",
    "NullNarrativeEngine",
]
