from __future__ import annotations

from dataclasses import dataclass, asdict, is_dataclass
from pathlib import Path
from typing import Iterable, Any, Iterator

from .ui_events import BubbleEvent, bubble_event_sort_key

from .schema import RunManifest, TickFrame, EventFrame, IntegrationSchemaVersion
from .util.stable_json import write_json, write_jsonl
from .frame_diff import compute_frame_diff


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
    ui_events: Iterable[BubbleEvent] | None = None,
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
    ui_events_rel = "ui_events/ui_events.jsonl"
    manifest_rel = "manifest.json"

    frames_list = list(frames)
    events_list = list(events) if events is not None else None
    ui_events_list = list(ui_events) if ui_events is not None else None

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
    if ui_events_list is not None:
        artifacts["ui_events"] = ui_events_rel

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
    if ui_events_list is not None:
        # Ensure deterministic ordering policy for BubbleEvents
        ordered_ui = sorted(ui_events_list, key=bubble_event_sort_key)
        write_jsonl(base / ui_events_rel, ordered_ui)

    return finalized


def _schema_version_str(v: IntegrationSchemaVersion | None) -> str:
    if isinstance(v, IntegrationSchemaVersion):
        return f"{int(v.major)}.{int(v.minor)}.{int(v.patch)}"
    # Fallback to 1.0.0 if absent
    return "1.0.0"


def export_replay(
    out_dir: Path | str,
    *,
    manifest: RunManifest,
    frames: Iterable[TickFrame],
    keyframe_interval: int = 100,
    ui_events: Iterable[BubbleEvent] | None = None,
) -> RunManifest:
    """Export a replay-ready, chunked store with keyframes, diffs, and an index.

    Layout (relative to out_dir):
        manifest.json
        index.json
        keyframes/000000.json
        diffs/000001.json

    Notes:
    - Computes diffs on the fly; does not retain full history in memory.
    - Deterministic file content and write order.
    - Paths in index are relative.
    """
    base = Path(out_dir)

    # Constants
    PAD = 6  # zero-pad width for tick filenames (lexical sort stability)

    # Prepare deterministic artifact paths
    manifest_rel = "manifest.json"
    index_rel = "index.json"
    keyframes_dir_rel = Path("keyframes")
    diffs_dir_rel = Path("diffs")
    ui_events_rel = Path("ui_events") / "ui_events.jsonl"

    # Iteration state
    prev_frame: TickFrame | None = None
    tick_min: int | None = None
    tick_max: int | None = None
    time_min: float | None = None
    time_max: float | None = None
    frame_count = 0

    # Index structure (deterministic): map str(tick) -> {keyframe, diffs: []}
    index_ticks: dict[str, dict[str, Any]] = {}

    # Ensure directories exist deterministically before writing
    (base / keyframes_dir_rel).mkdir(parents=True, exist_ok=True)
    (base / diffs_dir_rel).mkdir(parents=True, exist_ok=True)

    def tick_name(t: int) -> str:
        return str(t).zfill(PAD) + ".json"

    # Stream through frames once
    for curr in frames:
        t = int(curr.tick_index)
        # Update ranges deterministically
        if tick_min is None or t < tick_min:
            tick_min = t
        if tick_max is None or t > tick_max:
            tick_max = t
        if time_min is None or curr.time_seconds < time_min:
            time_min = float(curr.time_seconds)
        if time_max is None or curr.time_seconds > time_max:
            time_max = float(curr.time_seconds)
        frame_count += 1

        # Determine this tick's anchor keyframe tick (floor to interval)
        k_tick = (t // keyframe_interval) * keyframe_interval

        # If this tick is an anchor, write full keyframe
        if t == k_tick:
            k_rel = keyframes_dir_rel / tick_name(t)
            write_json(base / k_rel, curr)
        # Compute and write diff for every tick > minimal observed (including keyframe ticks?)
        # Per rules: One diff per tick; diff T transforms frame T-1 -> T
        if prev_frame is not None:
            d_rel = diffs_dir_rel / tick_name(t)
            diff = compute_frame_diff(prev_frame, curr)
            write_json(base / d_rel, diff)

        # Build index entry for this tick
        k_rel_path = keyframes_dir_rel / tick_name(k_tick)
        diffs_list: list[str] = []
        # diffs from k_tick+1 .. t (inclusive), but only if t >= k_tick
        start = k_tick + 1
        if prev_frame is None and t == k_tick:
            # First observed frame may be a keyframe with no prior diff
            pass
        if t >= start:
            # Build deterministic list of relative paths
            for dt in range(start, t + 1):
                diffs_list.append(str(diffs_dir_rel / tick_name(dt)))

        index_ticks[str(t)] = {
            "keyframe": str(k_rel_path),
            "diffs": diffs_list,
        }

        prev_frame = curr

    # Finalize manifest
    schema_version = (
        manifest.schema_version
        if isinstance(manifest.schema_version, IntegrationSchemaVersion)
        else IntegrationSchemaVersion(1, 0, 0)
    )

    finalized = RunManifest(
        schema_version=schema_version,
        run_id=manifest.run_id,
        world_id=manifest.world_id,
        episode_id=manifest.episode_id,
        tick_start=int(tick_min or 0),
        tick_end=int(tick_max or 0),
        frame_count=int(frame_count),
        time_start_seconds=time_min,
        time_end_seconds=time_max,
        artifacts={
            "manifest": manifest_rel,
            "index": index_rel,
            "keyframes": str(keyframes_dir_rel),
            "diffs": str(diffs_dir_rel),
            **({"ui_events": str(ui_events_rel)} if ui_events is not None else {}),
        },
        exported_at_utc_ms=manifest.exported_at_utc_ms,
    )

    # Write manifest and index deterministically at the end (after data files)
    write_json(base / manifest_rel, finalized)

    index_obj = {
        "schema_version": _schema_version_str(schema_version),
        "run_id": finalized.run_id,
        "episode_id": finalized.episode_id,
        "keyframe_interval": int(keyframe_interval),
        "ticks": index_ticks,
    }
    write_json(base / index_rel, index_obj)

    # Optional UI events stream (write after index for determinism of layout order)
    if ui_events is not None:
        # We need to realize iterable to apply sorting and stable write
        ui_list = list(ui_events)
        ui_list.sort(key=bubble_event_sort_key)
        write_jsonl(base / ui_events_rel, ui_list)

    return finalized


__all__ = ["ExportConfig", "export_run", "export_replay"]
