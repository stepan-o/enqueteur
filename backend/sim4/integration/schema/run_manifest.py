from dataclasses import dataclass
from .version import IntegrationSchemaVersion


@dataclass(frozen=True)
class RunManifest:
    """Deterministic, primitives-only run metadata for viewer/export.

    Pure DTO (frozen). No I/O, no clocks, no dynamic defaults. Rust-portable.
    """

    schema_version: IntegrationSchemaVersion

    run_id: int | None
    world_id: int
    episode_id: int | None

    tick_start: int
    tick_end: int
    frame_count: int

    time_start_seconds: float | None
    time_end_seconds: float | None

    # Relative artifact paths (e.g., {"manifest": "manifest.json", "frames": "frames/frames.jsonl"})
    artifacts: dict[str, str]

    # Optional, must be injected (do not compute here) to keep determinism in tests
    exported_at_utc_ms: int | None = None
