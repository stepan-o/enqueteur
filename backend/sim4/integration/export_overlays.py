from __future__ import annotations

"""
ARTIFACTS ONLY — NO REPLAY_ — NO LIVE SESSION

Sprint 14.7 — Overlay Sidecars Exporter

Exports presentation overlays as out-of-protocol sidecar streams using KVP
envelopes with X_* msg_types. Overlays are written as JSONL streams where
each line is an independently-decodable envelope. Discovery is manifest-driven
via OverlayPointer rel_path values; no implicit conventions.

Policies (v0.1):
- UI events are batched into fixed-size tick windows (batch_span_ticks, default 2)
  and written to overlays/ui_events.jsonl as X_UI_EVENT_BATCH envelopes.
  Batch end_tick is inclusive. Events may be empty in a batch (sparse allowed).
- Psycho frames are written one per envelope to overlays/psycho_frames.jsonl as
  X_PSYCHO_FRAME envelopes; typically one per tick (sampling is a producer choice).

Determinism:
- Events inside a batch are sorted by (tick, event_id)
- Psycho nodes sorted by id; edges sorted by (src_id, dst_id, kind)
- Float values in event/psycho data are quantized (Q1E3)
"""

from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
import json
import uuid

from .overlay_schemas import UIEventBatch, PsychoFrame
from .kvp_envelope import make_envelope, validate_envelope


def _write_jsonl(path: Path, envelopes: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write UTF-8 without BOM; each line is a compact JSON object
    with path.open("wb") as f:
        for env in envelopes:
            validate_envelope(env)
            s = json.dumps(env, ensure_ascii=False, separators=(",", ":"))
            f.write(s.encode("utf-8"))
            f.write(b"\n")


def export_ui_events_jsonl(
    run_root: str | Path,
    *,
    start_tick: int,
    end_tick: int,
    events: List[Dict[str, Any]],
    batch_span_ticks: int = 2,
    rel_path: str = "overlays/ui_events.jsonl",
) -> str:
    """Export UI events as X_UI_EVENT_BATCH envelopes to a JSONL file.

    - Batches cover [start, min(end, start+span-1)] inclusive windows, stepping by span
    - Events outside [start_tick, end_tick] are ignored (not written)
    - Returns the relative path used for the stream
    """
    root = Path(run_root)
    # Filter events to window and normalize minimal fields presence
    ev_norm: List[Dict[str, Any]] = []
    for e in events:
        if not isinstance(e, dict):
            continue
        if "tick" not in e or "event_id" not in e or "kind" not in e:
            continue
        t = int(e["tick"])  # type: ignore[arg-type]
        if t < start_tick or t > end_tick:
            continue
        data = e.get("data", {})
        if not isinstance(data, dict):
            data = {}
        ev_norm.append({"tick": t, "event_id": e["event_id"], "kind": e["kind"], "data": data})

    envelopes: List[Dict[str, Any]] = []
    # Build batches
    cur = start_tick
    while cur <= end_tick:
        win_end = min(end_tick, cur + batch_span_ticks - 1)
        batch_events = [e for e in ev_norm if cur <= e["tick"] <= win_end]
        batch = UIEventBatch(
            schema_version=__import__(
                "backend.sim4.integration.schema_version", fromlist=["INTEGRATION_SCHEMA_VERSION"]
            ).INTEGRATION_SCHEMA_VERSION,
            start_tick=cur,
            end_tick=win_end,
            events=batch_events,
        )
        payload = batch.to_dict()
        env = make_envelope("X_UI_EVENT_BATCH", payload, msg_id=str(uuid.uuid4()), sent_at_ms=0)
        envelopes.append(env)
        cur = win_end + 1

    out_path = root / rel_path
    _write_jsonl(out_path, envelopes)
    return rel_path


def export_psycho_frames_jsonl(
    run_root: str | Path,
    frames: Iterable[Dict[str, Any]],
    *,
    rel_path: str = "overlays/psycho_frames.jsonl",
) -> str:
    """Export psycho frames as X_PSYCHO_FRAME envelopes to JSONL.

    Frames dicts must contain: schema_version (optional; will be validated in from_dict),
    tick, nodes (list), edges (list). Extra fields are ignored.
    Returns the relative path used.
    """
    root = Path(run_root)
    envs: List[Dict[str, Any]] = []
    for fr in frames:
        if not isinstance(fr, dict):
            continue
        pf = PsychoFrame.from_dict(
            {
                "schema_version": __import__(
                    "backend.sim4.integration.schema_version", fromlist=["INTEGRATION_SCHEMA_VERSION"]
                ).INTEGRATION_SCHEMA_VERSION,
                "tick": fr.get("tick", 0),
                "nodes": fr.get("nodes", []),
                "edges": fr.get("edges", []),
            }
        )
        payload = pf.to_dict()
        env = make_envelope("X_PSYCHO_FRAME", payload, msg_id=str(uuid.uuid4()), sent_at_ms=0)
        envs.append(env)

    out_path = root / rel_path
    _write_jsonl(out_path, envs)
    return rel_path


__all__ = [
    "export_ui_events_jsonl",
    "export_psycho_frames_jsonl",
]
