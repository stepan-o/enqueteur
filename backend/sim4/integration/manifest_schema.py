from __future__ import annotations

"""Manifest v0.1 schema and validation for offline artifacts (Sprint 14.4).

This module defines the strictly validated manifest surface used by offline
viewers to discover everything needed to replay artifacts without scanning
directories or requiring a server.

Non‑negotiable (Sprint 14 scope lock): ARTIFACTS ONLY — NO REPLAY_* — NO LIVE SESSION

Key guarantees:
- kvp_version equals SSoT KVP_VERSION ("0.1")
- schema_version equals INTEGRATION_SCHEMA_VERSION
- run_anchors and render_spec validated via their own SSoT modules
- keyframe policy is XOR: either keyframe_interval or keyframe_ticks
- channels set is non-empty, deduped, allowed, and serialized in sorted order
- snapshots pointers cover every keyframe tick
- diffs inventory provides per‑tick transitions (from_tick -> to_tick=from+1)
- integrity covers every referenced pointer (inline content_sha256 or in map)

No IO or writer logic here beyond to_dict()/from_dict().
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .kvp_version import KVP_VERSION
from .schema_version import INTEGRATION_SCHEMA_VERSION
from .run_anchors import RunAnchors
from .render_spec import RenderSpec


ALLOWED_CHANNELS: Tuple[str, ...] = ("WORLD", "AGENTS", "ITEMS", "EVENTS", "DEBUG")
# Manifest pointer surface only: overlays are enumerated under manifest.overlays,
# so X_* message types are intentionally excluded here.
ALLOWED_MSG_TYPES_FOR_POINTERS: Tuple[str, ...] = ("FULL_SNAPSHOT", "FRAME_DIFF", "KERNEL_HELLO")


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _require_keys(d: Dict[str, Any], keys: List[str], ctx: str) -> None:
    missing = [k for k in keys if k not in d]
    if missing:
        raise ValueError(f"{ctx} missing required fields: {', '.join(missing)}")


def _int_keyed_dict_from(d: Dict[Any, Any]) -> Dict[int, Any]:
    out: Dict[int, Any] = {}
    for k, v in d.items():
        if isinstance(k, int):
            out[k] = v
        else:
            try:
                out[int(k)] = v
            except Exception as e:  # noqa: BLE001
                raise ValueError("Dictionary contains non-int key that cannot be coerced to int") from e
    return out


def _is_rel_path(p: str) -> bool:
    return isinstance(p, str) and p != "" and not p.startswith("/") and "://" not in p


@dataclass(frozen=True)
class RecordPointer:
    id: str
    rel_path: str
    format: str
    msg_type: str
    # For snapshots: tick; for diffs: from_tick/to_tick
    tick: Optional[int] = None
    from_tick: Optional[int] = None
    to_tick: Optional[int] = None
    byte_size: Optional[int] = None
    content_sha256: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "rel_path": self.rel_path,
            "format": self.format,
            "msg_type": self.msg_type,
        }
        if self.tick is not None:
            d["tick"] = int(self.tick)
        if self.from_tick is not None:
            d["from_tick"] = int(self.from_tick)
        if self.to_tick is not None:
            d["to_tick"] = int(self.to_tick)
        if self.byte_size is not None:
            d["byte_size"] = int(self.byte_size)
        if self.content_sha256 is not None:
            d["content_sha256"] = self.content_sha256
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RecordPointer":
        _require(isinstance(d, dict), "RecordPointer requires dict")
        _require_keys(d, ["id", "rel_path", "format", "msg_type"], "RecordPointer")
        _require(d["msg_type"] in ALLOWED_MSG_TYPES_FOR_POINTERS, "RecordPointer.msg_type not allowed")
        _require(_is_rel_path(d["rel_path"]), "RecordPointer.rel_path must be relative and offline-friendly")

        tick = d.get("tick")
        ft = d.get("from_tick")
        tt = d.get("to_tick")
        if tick is not None:
            tick = int(tick)
            _require(tick >= 0, "RecordPointer.tick must be >= 0")
        if ft is not None or tt is not None:
            _require(ft is not None and tt is not None, "RecordPointer diffs require both from_tick and to_tick")
            ft = int(ft)
            tt = int(tt)
            _require(ft >= 0 and tt > ft, "RecordPointer diff ticks invalid")

        bs = d.get("byte_size")
        if bs is not None:
            bs = int(bs)
            _require(bs >= 0, "RecordPointer.byte_size must be >= 0")

        cs = d.get("content_sha256")
        if cs is not None:
            _require(isinstance(cs, str) and len(cs) > 0, "content_sha256 must be non-empty string if present")

        return RecordPointer(
            id=d["id"],
            rel_path=d["rel_path"],
            format=d["format"],
            msg_type=d["msg_type"],
            tick=tick,
            from_tick=ft,
            to_tick=tt,
            byte_size=bs,
            content_sha256=cs,
        )


@dataclass(frozen=True)
class OverlayPointer:
    rel_path: str
    format: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"rel_path": self.rel_path, "format": self.format, "notes": self.notes}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "OverlayPointer":
        _require(isinstance(d, dict), "OverlayPointer requires dict")
        _require_keys(d, ["rel_path", "format"], "OverlayPointer")
        _require(_is_rel_path(d["rel_path"]), "OverlayPointer.rel_path must be relative")
        notes = d.get("notes")
        _require(notes is None or isinstance(notes, str), "OverlayPointer.notes must be str or None")
        return OverlayPointer(rel_path=d["rel_path"], format=d["format"], notes=notes)


@dataclass(frozen=True)
class LayoutHints:
    # Legacy/simple hints (kept for compatibility)
    records_dir: Optional[str] = None
    format: Optional[str] = None  # e.g., "SINGLE_JSON"
    # S14.5 extended hints for discoverability without scanning
    records_root: Optional[str] = None  # typically "."
    snapshots_dir: Optional[str] = None
    diffs_dir: Optional[str] = None
    overlays_dir: Optional[str] = None
    index_dir: Optional[str] = None
    diff_storage: Optional[str] = None  # "PER_TICK_FILES" | "JSONL_CHUNKS"

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.records_dir is not None:
            d["records_dir"] = self.records_dir
        if self.format is not None:
            d["format"] = self.format
        if self.records_root is not None:
            d["records_root"] = self.records_root
        if self.snapshots_dir is not None:
            d["snapshots_dir"] = self.snapshots_dir
        if self.diffs_dir is not None:
            d["diffs_dir"] = self.diffs_dir
        if self.overlays_dir is not None:
            d["overlays_dir"] = self.overlays_dir
        if self.index_dir is not None:
            d["index_dir"] = self.index_dir
        if self.diff_storage is not None:
            d["diff_storage"] = self.diff_storage
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "LayoutHints":
        _require(isinstance(d, dict), "LayoutHints requires dict")
        rd = d.get("records_dir")
        if rd is not None:
            _require(_is_rel_path(rd), "LayoutHints.records_dir must be relative if present")
        fmt = d.get("format")
        if fmt is not None:
            _require(isinstance(fmt, str) and fmt != "", "LayoutHints.format must be non-empty string if present")

        rroot = d.get("records_root")
        if rroot is not None:
            _require(_is_rel_path(rroot) or rroot == ".", "LayoutHints.records_root must be relative or '.'")
        sdir = d.get("snapshots_dir")
        if sdir is not None:
            _require(_is_rel_path(sdir), "LayoutHints.snapshots_dir must be relative if present")
        ddir = d.get("diffs_dir")
        if ddir is not None:
            _require(_is_rel_path(ddir), "LayoutHints.diffs_dir must be relative if present")
        odir = d.get("overlays_dir")
        if odir is not None:
            _require(_is_rel_path(odir), "LayoutHints.overlays_dir must be relative if present")
        idir = d.get("index_dir")
        if idir is not None:
            _require(_is_rel_path(idir), "LayoutHints.index_dir must be relative if present")
        dst = d.get("diff_storage")
        if dst is not None:
            _require(dst in ("PER_TICK_FILES", "JSONL_CHUNKS"), "LayoutHints.diff_storage invalid value")

        return LayoutHints(
            records_dir=rd,
            format=fmt,
            records_root=rroot,
            snapshots_dir=sdir,
            diffs_dir=ddir,
            overlays_dir=odir,
            index_dir=idir,
            diff_storage=dst,
        )


@dataclass(frozen=True)
class DiffInventory:
    # from_tick -> pointer (FRAME_DIFF covering from_tick -> from_tick+1)
    diffs_by_from_tick: Dict[int, RecordPointer]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "diffs_by_from_tick": {str(k): v.to_dict() for k, v in sorted(self.diffs_by_from_tick.items())}
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "DiffInventory":
        _require(isinstance(d, dict), "DiffInventory requires dict")
        _require("diffs_by_from_tick" in d and isinstance(d["diffs_by_from_tick"], dict),
                 "DiffInventory.diffs_by_from_tick must be a dict")
        raw: Dict[int, Any] = _int_keyed_dict_from(d["diffs_by_from_tick"])  # type: ignore[arg-type]
        out: Dict[int, RecordPointer] = {}
        for k, v in raw.items():
            rp = RecordPointer.from_dict(v)
            _require(rp.msg_type == "FRAME_DIFF", "DiffInventory expects FRAME_DIFF pointers")
            _require(rp.from_tick == k and rp.to_tick == k + 1,
                     "Diff pointer must have from_tick==key and to_tick==from_tick+1")
            out[k] = rp
        return DiffInventory(diffs_by_from_tick=out)

    def validate_coverage(self, start_tick: int, end_tick: int) -> None:
        # Ensure every transition from start to end-1 is present
        for t in range(start_tick, max(start_tick, end_tick)):
            _require(t in self.diffs_by_from_tick,
                     f"Missing diff for from_tick={t}")


@dataclass(frozen=True)
class IntegritySpec:
    hash_alg: str
    records_sha256: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {"hash_alg": self.hash_alg, "records_sha256": dict(sorted(self.records_sha256.items()))}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "IntegritySpec":
        _require(isinstance(d, dict), "IntegritySpec requires dict")
        _require_keys(d, ["hash_alg", "records_sha256"], "IntegritySpec")
        _require(d["hash_alg"] == "SHA-256", "IntegritySpec.hash_alg must be 'SHA-256'")
        mapping = d["records_sha256"]
        _require(isinstance(mapping, dict) and len(mapping) > 0, "records_sha256 must be a non-empty dict")
        for k, v in mapping.items():
            _require(isinstance(k, str) and k != "", "records_sha256 keys must be non-empty strings")
            _require(isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v.lower()),
                     "records_sha256 values must be lowercase sha256 hex")
        # Normalize to lowercase
        norm = {k: v.lower() for k, v in mapping.items()}
        return IntegritySpec(hash_alg="SHA-256", records_sha256=norm)

    def ensure_covers(self, pointers: List[RecordPointer]) -> None:
        for p in pointers:
            if p.content_sha256:
                # accept inline provided hashes
                continue
            covered = (p.id in self.records_sha256) or (p.rel_path in self.records_sha256)
            _require(covered, f"Integrity map missing SHA for pointer id or path: {p.id} / {p.rel_path}")


@dataclass(frozen=True)
class ManifestV0_1:
    kvp_version: str
    schema_version: str
    run_anchors: RunAnchors
    render_spec: RenderSpec
    available_start_tick: int
    available_end_tick: int
    channels: List[str]
    # XOR
    keyframe_interval: Optional[int]
    keyframe_ticks: Optional[List[int]]
    snapshots: Dict[int, RecordPointer]
    diffs: DiffInventory
    integrity: IntegritySpec
    layout: Optional[LayoutHints] = None
    overlays: Optional[Dict[str, OverlayPointer]] = None

    # ----- Helpers -----
    def _sorted_channels(self) -> List[str]:
        # stable, no duplicates
        return sorted(self.channels)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "kvp_version": self.kvp_version,
            "schema_version": self.schema_version,
            "run_anchors": self.run_anchors.to_dict(),
            "render_spec": self.render_spec.to_dict(),
            "available_start_tick": int(self.available_start_tick),
            "available_end_tick": int(self.available_end_tick),
            "channels": self._sorted_channels(),
            "snapshots": {str(k): v.to_dict() for k, v in sorted(self.snapshots.items())},
            "diffs": self.diffs.to_dict(),
            "integrity": self.integrity.to_dict(),
        }
        if self.keyframe_interval is not None:
            d["keyframe_interval"] = int(self.keyframe_interval)
        if self.keyframe_ticks is not None:
            d["keyframe_ticks"] = [int(x) for x in self.keyframe_ticks]
        if self.layout is not None:
            d["layout"] = self.layout.to_dict()
        if self.overlays is not None:
            d["overlays"] = {k: v.to_dict() for k, v in sorted(self.overlays.items())}
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ManifestV0_1":
        _require(isinstance(d, dict), "Manifest must be a dict")
        _require_keys(
            d,
            [
                "kvp_version",
                "schema_version",
                "run_anchors",
                "render_spec",
                "available_start_tick",
                "available_end_tick",
                "channels",
                "snapshots",
                "diffs",
                "integrity",
            ],
            "ManifestV0_1",
        )

        run_anchors = RunAnchors.from_dict(d["run_anchors"])  # type: ignore[arg-type]
        render_spec = RenderSpec.from_dict(d["render_spec"])  # type: ignore[arg-type]
        ast = int(d["available_start_tick"])  # type: ignore[arg-type]
        aend = int(d["available_end_tick"])  # type: ignore[arg-type]
        _require(ast >= 0, "available_start_tick must be >= 0")
        _require(aend >= ast, "available_end_tick must be >= available_start_tick")

        channels = list(d["channels"])  # type: ignore[arg-type]
        _require(isinstance(channels, list) and len(channels) > 0, "channels must be non-empty list")
        _require(all(isinstance(c, str) and c in ALLOWED_CHANNELS for c in channels), "channels contain unknown values")
        _require(len(set(channels)) == len(channels), "channels must not contain duplicates")

        # keyframe policy
        kint = d.get("keyframe_interval")
        kticks = d.get("keyframe_ticks")
        _require((kint is None) ^ (kticks is None), "Exactly one of keyframe_interval or keyframe_ticks must be present")
        if kint is not None:
            kint = int(kint)
            _require(kint >= 1, "keyframe_interval must be >= 1")
        if kticks is not None:
            _require(isinstance(kticks, list) and len(kticks) > 0, "keyframe_ticks must be a non-empty list")
            ticks = [int(x) for x in kticks]
            _require(all(ast <= t <= aend for t in ticks), "keyframe_ticks outside tick window")
            _require(sorted(ticks) == ticks and len(set(ticks)) == len(ticks), "keyframe_ticks must be strictly ascending and unique")
            kticks = ticks

        snapshots_raw: Dict[int, Any] = _int_keyed_dict_from(d["snapshots"])  # type: ignore[arg-type]
        snapshots: Dict[int, RecordPointer] = {}
        for t, val in snapshots_raw.items():
            rp = RecordPointer.from_dict(val)
            _require(rp.msg_type in ("FULL_SNAPSHOT", "KERNEL_HELLO"), "Snapshot pointers must be FULL_SNAPSHOT or KERNEL_HELLO where relevant")
            if rp.msg_type == "FULL_SNAPSHOT":
                _require(rp.tick == t, "Snapshot pointer tick must equal its key")
            snapshots[t] = rp

        diffs = DiffInventory.from_dict(d["diffs"])  # type: ignore[arg-type]
        integrity = IntegritySpec.from_dict(d["integrity"])  # type: ignore[arg-type]

        layout = d.get("layout")
        layout_obj = LayoutHints.from_dict(layout) if isinstance(layout, dict) else None
        overlays_dict = d.get("overlays")
        overlays: Optional[Dict[str, OverlayPointer]] = None
        if isinstance(overlays_dict, dict):
            overlays = {k: OverlayPointer.from_dict(v) for k, v in overlays_dict.items()}

        m = ManifestV0_1(
            kvp_version=str(d["kvp_version"]),
            schema_version=str(d["schema_version"]),
            run_anchors=run_anchors,
            render_spec=render_spec,
            available_start_tick=ast,
            available_end_tick=aend,
            channels=channels,
            keyframe_interval=kint if isinstance(kint, int) else None,
            keyframe_ticks=kticks if isinstance(kticks, list) else None,
            snapshots=snapshots,
            diffs=diffs,
            integrity=integrity,
            layout=layout_obj,
            overlays=overlays,
        )
        # Run validation after hydrate
        m.validate()
        return m

    def derive_keyframe_ticks(self) -> List[int]:
        if self.keyframe_ticks is not None:
            return list(self.keyframe_ticks)
        # interval implied
        assert self.keyframe_interval is not None
        ticks: List[int] = []
        k = self.keyframe_interval
        # include start as a keyframe and then every k
        t = self.available_start_tick
        while t <= self.available_end_tick:
            ticks.append(t)
            t += k  # type: ignore[operator]
        return ticks

    def validate(self) -> None:
        _require(self.kvp_version == KVP_VERSION, "kvp_version must equal SSoT KVP_VERSION")
        _require(self.schema_version == INTEGRATION_SCHEMA_VERSION, "schema_version must equal INTEGRATION_SCHEMA_VERSION")
        _require(self.available_start_tick >= 0, "available_start_tick must be >= 0")
        _require(self.available_end_tick >= self.available_start_tick, "available_end_tick must be >= available_start_tick")

        # Channels
        _require(len(self.channels) > 0, "channels must be non-empty")
        _require(len(set(self.channels)) == len(self.channels), "channels must not contain duplicates")
        for c in self.channels:
            _require(c in ALLOWED_CHANNELS, f"Unknown channel: {c}")

        # keyframe policy XOR
        _require((self.keyframe_interval is None) ^ (self.keyframe_ticks is None),
                 "Exactly one keyframe policy must be provided: interval XOR ticks")
        if self.keyframe_interval is not None:
            _require(self.keyframe_interval >= 1, "keyframe_interval must be >= 1")
        if self.keyframe_ticks is not None:
            ticks = self.keyframe_ticks
            _require(len(ticks) > 0, "keyframe_ticks must be non-empty")
            _require(sorted(ticks) == list(ticks) and len(set(ticks)) == len(ticks),
                     "keyframe_ticks must be strictly ascending and unique")
            _require(all(self.available_start_tick <= t <= self.available_end_tick for t in ticks),
                     "keyframe_ticks outside available window")

        # snapshots coverage for keyframes
        kf_ticks = self.derive_keyframe_ticks()
        for t in kf_ticks:
            _require(t in self.snapshots and self.snapshots[t].msg_type == "FULL_SNAPSHOT",
                     f"Missing FULL_SNAPSHOT pointer for keyframe tick {t}")

        # diffs coverage for transitions
        self.diffs.validate_coverage(self.available_start_tick, self.available_end_tick)

        # integrity coverage
        all_ptrs: List[RecordPointer] = list(self.snapshots.values()) + list(self.diffs.diffs_by_from_tick.values())
        self.integrity.ensure_covers(all_ptrs)


__all__ = [
    "ALLOWED_CHANNELS",
    "RecordPointer",
    "OverlayPointer",
    "LayoutHints",
    "DiffInventory",
    "IntegritySpec",
    "ManifestV0_1",
]
