from __future__ import annotations

from dataclasses import dataclass, asdict, is_dataclass
from pathlib import Path
from typing import Iterable, Any

from .schema import RunManifest, TickFrame, EventFrame, IntegrationSchemaVersion
from .util.stable_json import write_json, write_jsonl


@dataclass(frozen=True)
class ExportConfig:
    """Optional configuration for export determinism.

    - exported_at_utc_ms: must be injected by caller if desired; exporter will
      not look at wall clock.
    """

    exported_at_utc_ms: int | None = None


def _to_primitive_list(objs: Iterable[Any]) -> list[Any]:
    out: list[Any] = []
    for o in objs:
        if is_dataclass(o):
            out.append(asdict(o))
        else:
            out.append(o)
    return out


def export_run(
    out_dir: Path | str,
    *,
    manifest: RunManifest,
    frames: Iterable[TickFrame],
    events: Iterable[EventFrame] | None = None,
    config: ExportConfig | None = None,
) -> RunManifest:
    """Write a minimal deterministic export for a run.

    Layout:
        out_dir/
          manifest.json
          frames/frames.jsonl
          events/events.jsonl (optional)

    Returns a finalized RunManifest (new instance), without mutating the input.
    """
    base = Path(out_dir)
    frames_rel = "frames/frames.jsonl"
    events_rel = "events/events.jsonl"
    manifest_rel = "manifest.json"

    frames_list = list(frames)
    events_list = list(events) if events is not None else None

    # Determine tick/time ranges and counts from frames sequence (input order preserved)
    if frames_list:
        ticks = [f.tick_index for f in frames_list]
        times = [f.time_seconds for f in frames_list]
        tick_start = int(min(ticks))
        tick_end = int(max(ticks))
        frame_count = len(frames_list)
        time_start = float(min(times)) if times else None
        time_end = float(max(times)) if times else None
    else:
        # Empty export is allowed but unusual; keep deterministic zeros
        tick_start = 0
        tick_end = 0
        frame_count = 0
        time_start = None
        time_end = None

    # Artifacts table: relative paths only
    artifacts: dict[str, str] = {
        "manifest": manifest_rel,
        "frames": frames_rel,
    }
    if events_list is not None:
        artifacts["events"] = events_rel

    # exported_at is only pulled from provided manifest or config; no clocks here
    exported_at_utc_ms = manifest.exported_at_utc_ms
    if exported_at_utc_ms is None and config is not None:
        exported_at_utc_ms = config.exported_at_utc_ms

    # Compute episode_id and schema_version pass-through
    schema_version = manifest.schema_version if isinstance(manifest.schema_version, IntegrationSchemaVersion) else IntegrationSchemaVersion(1, 0, 0)

    finalized = RunManifest(
        schema_version=schema_version,
        run_id=manifest.run_id,
        world_id=manifest.world_id,
        episode_id=manifest.episode_id,
        tick_start=tick_start,
        tick_end=tick_end,
        frame_count=frame_count,
        time_start_seconds=time_start,
        time_end_seconds=time_end,
        artifacts=artifacts,
        exported_at_utc_ms=exported_at_utc_ms,
    )

    # Write manifest and streams deterministically
    write_json(base / manifest_rel, finalized)
    write_jsonl(base / frames_rel, frames_list)
    if events_list is not None:
        write_jsonl(base / events_rel, events_list)

    return finalized


__all__ = ["ExportConfig", "export_run"]
