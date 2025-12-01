from __future__ import annotations

from dataclasses import dataclass


# Episode Metadata


@dataclass(frozen=True)
class EpisodeMeta:
    episode_id: int
    title: str
    synopsis: str

    tick_start: int
    tick_end: int
    duration_seconds: float

    created_at_ms: int | None


# Episode Mood


@dataclass(frozen=True)
class EpisodeMood:
    tension_avg: float
    tension_peak: float
    sentiment_valence: float
    social_cohesion: float

    summary_label: str | None


# Scene & Time Structure


@dataclass(frozen=True)
class TensionSample:
    tick_index: int
    tension: float


@dataclass(frozen=True)
class SceneSnapshot:
    scene_id: int
    label: str

    tick_start: int
    tick_end: int

    focus_room_id: int | None
    focus_agent_ids: list[int]

    tension_curve: list[TensionSample]


@dataclass(frozen=True)
class DayWithScenes:
    day_index: int
    label: str
    scenes: list[SceneSnapshot]


# Final Episode Object


@dataclass(frozen=True)
class EpisodeNarrativeFragment:
    tick_index: int
    agent_id: int | None
    room_id: int | None
    text: str
    importance: float


@dataclass(frozen=True)
class StageEpisodeV2:
    meta: EpisodeMeta
    mood: EpisodeMood

    days: list[DayWithScenes]

    key_world_snapshots: list["WorldSnapshot"]
    key_agent_timelines: dict[int, list["WorldSnapshot"]]

    narrative_fragments: list[EpisodeNarrativeFragment]


__all__ = [
    "EpisodeMeta",
    "EpisodeMood",
    "TensionSample",
    "SceneSnapshot",
    "DayWithScenes",
    "EpisodeNarrativeFragment",
    "StageEpisodeV2",
]
