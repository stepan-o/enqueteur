from __future__ import annotations

"""Draft LIVE transport adapter for KVP-0001 (v0.1).

This module provides a minimal session state machine for LIVE transports:
- handles VIEWER_HELLO and SUBSCRIBE
- sends KERNEL_HELLO and SUBSCRIBED
- publishes FULL_SNAPSHOT and FRAME_DIFF after subscription

It is intentionally integration-only and does not import runtime/ecs/world.
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence
import uuid

from .manifest_schema import ALLOWED_CHANNELS
from .run_anchors import RunAnchors
from .render_spec import RenderSpec
from .live_envelope import make_live_envelope, validate_live_envelope


class LiveTransport(Protocol):
    """Minimal transport interface for LIVE sessions."""

    def send(self, data: bytes) -> None: ...


class LiveCodec(Protocol):
    """Codec boundary for LIVE session envelopes."""

    def encode(self, envelope: Dict[str, Any]) -> bytes: ...

    def decode(self, data: bytes) -> Dict[str, Any]: ...


@dataclass(frozen=True)
class LiveViewerInfo:
    viewer_name: str
    viewer_version: str
    supported_schema_versions: List[str]
    supports: Dict[str, Any]


class LiveSession:
    """KVP LIVE session coordinator (draft)."""

    def __init__(
        self,
        *,
        transport: LiveTransport,
        codec: LiveCodec,
        run_anchors: RunAnchors,
        render_spec: RenderSpec,
    ) -> None:
        self._transport = transport
        self._codec = codec
        self._run_anchors = run_anchors
        self._render_spec = render_spec

        self._viewer: LiveViewerInfo | None = None
        self._handshake_complete = False
        self._subscribed = False
        self._stream_id: str | None = None
        self._effective_channels: List[str] = []
        self._snapshot_policy: str | None = None
        self._baseline_sent = False

    # --- Public entry points ---
    def handle_incoming(self, data: bytes) -> None:
        """Decode, validate, and dispatch a single inbound LIVE envelope."""
        env = self._codec.decode(data)
        validate_live_envelope(env)
        msg_type = env.get("msg_type")
        payload = env.get("payload", {})

        if msg_type == "VIEWER_HELLO":
            self._on_viewer_hello(payload)
        elif msg_type == "SUBSCRIBE":
            self._on_subscribe(payload)
        elif msg_type == "PING":
            self._on_ping(payload)
        else:
            # Unknown or unsupported in this draft
            self._send_error(
                code="UNSUPPORTED_MESSAGE",
                message=f"Unsupported msg_type: {msg_type}",
                fatal=False,
            )

    def publish_full_snapshot(self, payload: Dict[str, Any]) -> None:
        """Send FULL_SNAPSHOT after subscription (caller provides payload)."""
        if not self._subscribed:
            self._send_error(code="NOT_SUBSCRIBED", message="Cannot send snapshot before SUBSCRIBED", fatal=True)
            return
        self._baseline_sent = True
        self._send("FULL_SNAPSHOT", payload)

    def publish_frame_diff(self, payload: Dict[str, Any]) -> None:
        """Send FRAME_DIFF after subscription (caller provides payload)."""
        if not self._subscribed:
            self._send_error(code="NOT_SUBSCRIBED", message="Cannot send diff before SUBSCRIBED", fatal=True)
            return
        if self._snapshot_policy == "ON_JOIN" and not self._baseline_sent:
            self._send_error(code="MISSING_BASELINE", message="Baseline snapshot required before diffs", fatal=True)
            return
        self._send("FRAME_DIFF", payload)

    # --- Internal handlers ---
    def _on_viewer_hello(self, payload: Dict[str, Any]) -> None:
        try:
            viewer_name = str(payload["viewer_name"])
            viewer_version = str(payload["viewer_version"])
            supported = list(payload["supported_schema_versions"])
            supports = dict(payload.get("supports", {}))
        except Exception as e:  # noqa: BLE001
            self._send_error(code="INVALID_VIEWER_HELLO", message="Malformed VIEWER_HELLO payload", fatal=True)
            raise ValueError("Malformed VIEWER_HELLO payload") from e

        if not supported:
            self._send_error(code="SCHEMA_MISMATCH", message="supported_schema_versions must be non-empty", fatal=True)
            return
        if self._run_anchors.schema_version not in supported:
            self._send_error(
                code="SCHEMA_MISMATCH",
                message=f"Viewer does not support schema_version={self._run_anchors.schema_version}",
                fatal=True,
            )
            return

        self._viewer = LiveViewerInfo(
            viewer_name=viewer_name,
            viewer_version=viewer_version,
            supported_schema_versions=[str(x) for x in supported],
            supports=supports,
        )
        self._handshake_complete = True

        self._send(
            "KERNEL_HELLO",
            {
                "engine_name": self._run_anchors.engine_name,
                "engine_version": self._run_anchors.engine_version,
                "schema_version": self._run_anchors.schema_version,
                "world_id": self._run_anchors.world_id,
                "run_id": self._run_anchors.run_id,
                "seed": self._run_anchors.seed,
                "tick_rate_hz": self._run_anchors.tick_rate_hz,
                "time_origin_ms": self._run_anchors.time_origin_ms,
                "render_spec": self._render_spec.to_dict(),
            },
        )

    def _on_subscribe(self, payload: Dict[str, Any]) -> None:
        if not self._handshake_complete:
            self._send_error(code="BAD_SEQUENCE", message="SUBSCRIBE before handshake", fatal=True)
            return

        stream = str(payload.get("stream", ""))
        if stream != "LIVE":
            self._send_error(code="INVALID_STREAM", message="Only stream=LIVE is allowed in v0.1", fatal=True)
            return

        channels = list(payload.get("channels", []))
        if not channels:
            self._send_error(code="INVALID_CHANNELS", message="channels must be non-empty", fatal=True)
            return
        if len(set(channels)) != len(channels):
            self._send_error(code="INVALID_CHANNELS", message="channels must not contain duplicates", fatal=True)
            return
        for c in channels:
            if c not in ALLOWED_CHANNELS:
                self._send_error(code="INVALID_CHANNELS", message=f"Unknown channel: {c}", fatal=True)
                return

        diff_policy = str(payload.get("diff_policy", "DIFF_ONLY"))
        snapshot_policy = str(payload.get("snapshot_policy", "ON_JOIN"))
        compression = str(payload.get("compression", "NONE"))

        self._subscribed = True
        self._stream_id = str(uuid.uuid4())
        self._effective_channels = list(channels)
        self._snapshot_policy = snapshot_policy
        self._baseline_sent = False

        self._send(
            "SUBSCRIBED",
            {
                "stream_id": self._stream_id,
                "effective_stream": "LIVE",
                "effective_channels": list(channels),
                "effective_diff_policy": diff_policy,
                "effective_snapshot_policy": snapshot_policy,
                "effective_compression": compression,
            },
        )

    def _on_ping(self, payload: Dict[str, Any]) -> None:
        # Echo nonce if present
        nonce = payload.get("nonce")
        self._send("PONG", {"nonce": nonce} if nonce is not None else {})

    # --- Send helpers ---
    def _send(self, msg_type: str, payload: Dict[str, Any]) -> None:
        env = make_live_envelope(
            msg_type,
            payload,
            msg_id=str(uuid.uuid4()),
            sent_at_ms=0,
        )
        data = self._codec.encode(env)
        self._transport.send(data)

    def _send_error(self, *, code: str, message: str, fatal: bool) -> None:
        self._send(
            "ERROR",
            {
                "code": code,
                "message": message,
                "fatal": bool(fatal),
            },
        )


__all__ = ["LiveTransport", "LiveCodec", "LiveSession", "LiveViewerInfo"]
