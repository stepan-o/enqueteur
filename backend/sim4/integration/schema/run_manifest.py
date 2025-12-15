from dataclasses import dataclass
from .version import IntegrationSchemaVersion


@dataclass(frozen=True)
class RunManifest:
    """Deterministic, replay-safe run metadata for viewer consumption.

    Pure data only. No I/O, no clocks, no dynamic defaults.
    """

    schema_version: IntegrationSchemaVersion

    run_id: int
    world_id: int
    scenario_seed: int

    tick_start: int
    tick_end: int
    tick_rate: float

    snapshot_interval: int  # keyframe cadence
    diff_interval: int  # diff cadence

    has_narrative: bool
    has_replay: bool
    has_psycho_topology: bool

    notes: str | None
