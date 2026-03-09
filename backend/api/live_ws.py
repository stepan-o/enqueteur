from __future__ import annotations

"""Enqueteur LIVE WebSocket entrypoint and run-attachment host.

Phase D2 scope:
- attach incoming websocket connections to already-created runs
- enforce KVP-ENQ-0001 handshake + subscribe lifecycle
- validate protocol envelopes and sequencing via explicit state machine

State streaming and gameplay command execution are intentionally deferred.
"""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
import asyncio
import json
import uuid

from backend.sim4.case_mbam import (
    DialogueTurnRequest,
    DialogueTurnSlotValue,
    InvestigationCommandAck,
    build_visible_dialogue_projection,
    build_visible_investigation_projection,
    build_visible_learning_projection,
    build_visible_npc_semantic_projection,
    build_visible_outcome_projection,
    build_visible_run_recap_projection,
    make_investigation_command,
)
from backend.sim4.host.kvp_defaults import DEFAULT_ENGINE_VERSION, default_render_spec
from backend.sim4.integration.canonicalize import canonicalize_state_obj
from backend.sim4.integration.live_envelope import make_live_envelope, validate_live_envelope
from backend.sim4.integration.step_hash import compute_step_hash

from .cases_start import (
    DEFAULT_CLOCK_DT_SECONDS,
    ENQUETEUR_ENGINE_NAME,
    ENQUETEUR_SCHEMA_VERSION,
    CaseRunRegistry,
    StartedCaseRun,
    extract_run_id_from_connection_target,
    get_default_case_run_registry,
)
from .live_commands import (
    CommandDispatchResult,
    DialogueTurnCommandPayload,
    InvestigateObjectCommandPayload,
    InputCommandValidationError,
    MinigameSubmitCommandPayload,
    ParsedInputCommand,
    parse_enqueteur_input_command,
)

ENQUETEUR_LIVE_WS_PATH = "/live"
RUN_NOT_FOUND_WS_CLOSE_CODE = 4404
RUN_NOT_FOUND_WS_CLOSE_REASON = "RUN_NOT_FOUND"
PROTOCOL_VIOLATION_WS_CLOSE_CODE = 1002
PROTOCOL_VIOLATION_WS_CLOSE_REASON = "PROTOCOL_VIOLATION"
INTERNAL_RUNTIME_WS_CLOSE_CODE = 1011
INTERNAL_RUNTIME_WS_CLOSE_REASON = "INTERNAL_RUNTIME_ERROR"

ENQUETEUR_ALLOWED_CHANNELS: tuple[str, ...] = (
    "WORLD",
    "NPCS",
    "INVESTIGATION",
    "DIALOGUE",
    "LEARNING",
    "EVENTS",
    "DEBUG",
)
ALLOWED_DIFF_POLICIES: tuple[str, ...] = ("DIFF_ONLY", "PERIODIC_SNAPSHOT", "SNAPSHOT_ON_DESYNC")
ALLOWED_SNAPSHOT_POLICIES: tuple[str, ...] = ("ON_JOIN", "NEVER")
ALLOWED_COMPRESSION_POLICIES: tuple[str, ...] = ("NONE",)
ENQUETEUR_MINIGAME_ID_ALIASES: dict[str, str] = {
    "MG1": "MG1_LABEL_READING",
    "MG1_LABEL_READING": "MG1_LABEL_READING",
    "MG2": "MG2_BADGE_LOG",
    "MG2_BADGE_LOG": "MG2_BADGE_LOG",
    "MG3": "MG3_RECEIPT_READING",
    "MG3_RECEIPT_READING": "MG3_RECEIPT_READING",
    "MG4": "MG4_TORN_NOTE_RECONSTRUCTION",
    "MG4_TORN_NOTE_RECONSTRUCTION": "MG4_TORN_NOTE_RECONSTRUCTION",
}
ENQUETEUR_MINIGAME_TARGETS: dict[str, str] = {
    "MG1_LABEL_READING": "O3_WALL_LABEL",
    "MG2_BADGE_LOG": "O6_BADGE_TERMINAL",
    "MG3_RECEIPT_READING": "O9_RECEIPT_PRINTER",
    "MG4_TORN_NOTE_RECONSTRUCTION": "O4_BENCH",
}
ENQUETEUR_MINIGAME_ACTION_PLAN: dict[str, tuple[tuple[str, str], ...]] = {
    "MG1_LABEL_READING": (
        ("O3_WALL_LABEL", "read"),
    ),
    "MG2_BADGE_LOG": (
        ("O6_BADGE_TERMINAL", "request_access"),
        ("O6_BADGE_TERMINAL", "view_logs"),
    ),
    "MG3_RECEIPT_READING": (
        ("O9_RECEIPT_PRINTER", "ask_for_receipt"),
        ("O9_RECEIPT_PRINTER", "read_receipt"),
    ),
    "MG4_TORN_NOTE_RECONSTRUCTION": (
        ("O4_BENCH", "inspect"),
    ),
}

LiveProtocolPhase = Literal["CONNECTED", "HANDSHAKING", "SUBSCRIBED", "CLOSED"]
LiveProtocolState = Literal["AWAITING_VIEWER_HELLO", "AWAITING_SUBSCRIBE", "SUBSCRIBED", "CLOSED"]


class EnqueteurWebSocketTransport(Protocol):
    """Minimal async websocket boundary for framework adapters."""

    async def accept(self) -> None: ...

    async def close(self, code: int = 1000, reason: str = "") -> None: ...

    async def send_text(self, data: str) -> None: ...


class RunLookupError(LookupError):
    """Raised when a LIVE websocket cannot be mapped to a known started run."""

    def __init__(self, *, connection_target: str, run_id_hint: str | None = None) -> None:
        message = (
            f"No started run found for run_id={run_id_hint}."
            if run_id_hint
            else "No started run found for websocket connection target."
        )
        super().__init__(message)
        self.connection_target = connection_target
        self.run_id_hint = run_id_hint


class ProtocolViolationError(ValueError):
    """Raised for invalid KVP envelopes, sequencing, or payload validation failures."""

    def __init__(self, *, code: str, message: str, fatal: bool = True) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.fatal = bool(fatal)


@dataclass(frozen=True)
class EnqueteurViewerHello:
    viewer_name: str
    viewer_version: str
    supported_schema_versions: tuple[str, ...]
    supports: dict[str, Any]


@dataclass(frozen=True)
class EnqueteurSubscribedConfig:
    stream_id: str
    effective_stream: str
    effective_channels: tuple[str, ...]
    effective_diff_policy: str
    effective_snapshot_policy: str
    effective_compression: str


@dataclass(frozen=True)
class EnqueteurRunBinding:
    """Stable run metadata bound to an attached websocket session."""

    run_id: str
    world_id: str
    case_id: str
    seed: str | int
    difficulty_profile: str
    mode: str
    ws_url: str
    started_at: str
    engine_name: str
    engine_version: str
    schema_version: str
    tick_rate_hz: int
    time_origin_ms: int
    render_spec: dict[str, Any]

    @classmethod
    def from_started_case_run(cls, record: StartedCaseRun) -> "EnqueteurRunBinding":
        tick_rate_hz = int(round(1.0 / DEFAULT_CLOCK_DT_SECONDS))
        if tick_rate_hz <= 0:
            raise ValueError("DEFAULT_CLOCK_DT_SECONDS must resolve to a positive tick_rate_hz")

        return cls(
            run_id=record.run_id,
            world_id=record.world_id,
            case_id=record.request.case_id,
            seed=record.request.seed,
            difficulty_profile=record.request.difficulty_profile,
            mode=record.request.mode,
            ws_url=record.ws_url,
            started_at=record.started_at,
            engine_name=ENQUETEUR_ENGINE_NAME,
            engine_version=DEFAULT_ENGINE_VERSION,
            schema_version=ENQUETEUR_SCHEMA_VERSION,
            tick_rate_hz=tick_rate_hz,
            time_origin_ms=0,
            render_spec=default_render_spec().to_dict(),
        )


@dataclass
class EnqueteurLiveSession:
    """Per-connection LIVE session container with explicit protocol state."""

    connection_id: str
    run: EnqueteurRunBinding
    phase: LiveProtocolPhase
    protocol_state: LiveProtocolState
    connected_at: str
    viewer_hello: EnqueteurViewerHello | None = None
    subscribed_config: EnqueteurSubscribedConfig | None = None
    baseline_sent: bool = False
    baseline_tick: int | None = None
    last_state: dict[str, Any] | None = None
    last_step_hash: str | None = None
    last_tick: int | None = None
    closed_at: str | None = None
    close_code: int | None = None
    close_reason: str | None = None


class EnqueteurLiveSessionHost:
    """Attach websocket connections to pre-started deterministic Enqueteur runs."""

    def __init__(self, *, run_registry: CaseRunRegistry | None = None) -> None:
        self._run_registry = run_registry if run_registry is not None else get_default_case_run_registry()
        self._sessions: dict[str, EnqueteurLiveSession] = {}
        self._closed_sessions: dict[str, EnqueteurLiveSession] = {}
        self._input_command_handlers = {
            "INVESTIGATE_OBJECT": self._dispatch_investigate_object,
            "DIALOGUE_TURN": self._dispatch_dialogue_turn,
            "MINIGAME_SUBMIT": self._dispatch_minigame_submit,
            "ATTEMPT_RECOVERY": self._dispatch_attempt_recovery,
            "ATTEMPT_ACCUSATION": self._dispatch_attempt_accusation,
        }

    def attach_connection(self, *, connection_target: str) -> EnqueteurLiveSession:
        record = self._run_registry.resolve_connection_target(connection_target)
        if record is None:
            raise RunLookupError(
                connection_target=connection_target,
                run_id_hint=extract_run_id_from_connection_target(connection_target),
            )

        session = EnqueteurLiveSession(
            connection_id=str(uuid.uuid4()),
            run=EnqueteurRunBinding.from_started_case_run(record),
            phase="CONNECTED",
            protocol_state="AWAITING_VIEWER_HELLO",
            connected_at=datetime.now(UTC).isoformat(),
        )
        self._sessions[session.connection_id] = session
        return session

    def mark_handshaking(self, connection_id: str) -> EnqueteurLiveSession:
        session = self._require_session(connection_id)
        if session.phase != "CLOSED":
            session.phase = "HANDSHAKING"
        return session

    def mark_subscribed(self, connection_id: str) -> EnqueteurLiveSession:
        session = self._require_session(connection_id)
        if session.phase != "CLOSED":
            session.phase = "SUBSCRIBED"
            session.protocol_state = "SUBSCRIBED"
        return session

    def record_viewer_hello(self, connection_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        session = self._require_session(connection_id)
        self._require_protocol_state(session, "AWAITING_VIEWER_HELLO", action="VIEWER_HELLO")

        viewer_name = _require_non_empty_str(payload.get("viewer_name"), field="viewer_name", code="INVALID_VIEWER_HELLO")
        viewer_version = _require_non_empty_str(
            payload.get("viewer_version"),
            field="viewer_version",
            code="INVALID_VIEWER_HELLO",
        )
        supported_schema_versions = _require_string_list(
            payload.get("supported_schema_versions"),
            field="supported_schema_versions",
            code="INVALID_VIEWER_HELLO",
            non_empty=True,
        )
        if ENQUETEUR_SCHEMA_VERSION not in supported_schema_versions:
            raise ProtocolViolationError(
                code="SCHEMA_MISMATCH",
                message=(
                    "Viewer does not support schema_version="
                    f"{ENQUETEUR_SCHEMA_VERSION}."
                ),
                fatal=True,
            )

        supports = payload.get("supports", {})
        if not isinstance(supports, dict):
            raise ProtocolViolationError(
                code="INVALID_VIEWER_HELLO",
                message="supports must be an object when provided.",
                fatal=True,
            )

        session.viewer_hello = EnqueteurViewerHello(
            viewer_name=viewer_name,
            viewer_version=viewer_version,
            supported_schema_versions=tuple(supported_schema_versions),
            supports=dict(supports),
        )
        session.protocol_state = "AWAITING_SUBSCRIBE"

        return {
            "engine_name": session.run.engine_name,
            "engine_version": session.run.engine_version,
            "schema_version": session.run.schema_version,
            "world_id": session.run.world_id,
            "run_id": session.run.run_id,
            "seed": session.run.seed,
            "tick_rate_hz": session.run.tick_rate_hz,
            "time_origin_ms": session.run.time_origin_ms,
            "render_spec": session.run.render_spec,
        }

    def record_subscribe(self, connection_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        session = self._require_session(connection_id)
        self._require_protocol_state(session, "AWAITING_SUBSCRIBE", action="SUBSCRIBE")

        stream = _require_non_empty_str(payload.get("stream"), field="stream", code="INVALID_SUBSCRIPTION")
        if stream != "LIVE":
            raise ProtocolViolationError(
                code="INVALID_SUBSCRIPTION",
                message="SUBSCRIBE.stream must be LIVE.",
                fatal=True,
            )

        channels = _require_string_list(
            payload.get("channels"),
            field="channels",
            code="INVALID_SUBSCRIPTION",
            non_empty=True,
        )
        if len(set(channels)) != len(channels):
            raise ProtocolViolationError(
                code="INVALID_SUBSCRIPTION",
                message="SUBSCRIBE.channels must not contain duplicates.",
                fatal=True,
            )
        unknown = [c for c in channels if c not in ENQUETEUR_ALLOWED_CHANNELS]
        if unknown:
            raise ProtocolViolationError(
                code="INVALID_SUBSCRIPTION",
                message=f"SUBSCRIBE.channels contains unsupported values: {', '.join(unknown)}.",
                fatal=True,
            )

        diff_policy = str(payload.get("diff_policy", "DIFF_ONLY"))
        snapshot_policy = str(payload.get("snapshot_policy", "ON_JOIN"))
        compression = str(payload.get("compression", "NONE"))
        if diff_policy not in ALLOWED_DIFF_POLICIES:
            raise ProtocolViolationError(
                code="INVALID_SUBSCRIPTION",
                message=f"Unsupported diff_policy '{diff_policy}'.",
                fatal=True,
            )
        if snapshot_policy not in ALLOWED_SNAPSHOT_POLICIES:
            raise ProtocolViolationError(
                code="INVALID_SUBSCRIPTION",
                message=f"Unsupported snapshot_policy '{snapshot_policy}'.",
                fatal=True,
            )
        if compression not in ALLOWED_COMPRESSION_POLICIES:
            raise ProtocolViolationError(
                code="INVALID_SUBSCRIPTION",
                message=f"Unsupported compression '{compression}'.",
                fatal=True,
            )

        config = EnqueteurSubscribedConfig(
            stream_id=str(uuid.uuid4()),
            effective_stream="LIVE",
            effective_channels=tuple(channels),
            effective_diff_policy=diff_policy,
            effective_snapshot_policy=snapshot_policy,
            effective_compression=compression,
        )
        session.subscribed_config = config
        self.mark_subscribed(connection_id)

        return {
            "stream_id": config.stream_id,
            "effective_stream": config.effective_stream,
            "effective_channels": list(config.effective_channels),
            "effective_diff_policy": config.effective_diff_policy,
            "effective_snapshot_policy": config.effective_snapshot_policy,
            "effective_compression": config.effective_compression,
        }

    def can_deliver_state(self, connection_id: str) -> bool:
        session = self._require_session(connection_id)
        return session.protocol_state == "SUBSCRIBED" and session.phase == "SUBSCRIBED"

    def dispatch_input_command(
        self,
        connection_id: str,
        command: ParsedInputCommand,
    ) -> CommandDispatchResult:
        """Route a validated INPUT_COMMAND to the Enqueteur command handler skeleton."""

        session = self._require_session(connection_id)
        started_run = self._require_started_run(session)
        handler = self._input_command_handlers.get(command.cmd_type)
        if handler is None:
            return CommandDispatchResult.rejected_result(
                client_cmd_id=command.client_cmd_id,
                reason_code="INVALID_COMMAND",
                message=f"Unsupported command type '{command.cmd_type}'.",
            )
        return handler(started_run=started_run, session=session, command=command)

    def can_stream_frame_diff(self, connection_id: str) -> bool:
        session = self._require_session(connection_id)
        return (
            session.protocol_state == "SUBSCRIBED"
            and session.phase == "SUBSCRIBED"
            and session.baseline_sent
            and session.last_state is not None
            and session.last_step_hash is not None
            and session.last_tick is not None
        )

    def build_full_snapshot_payload(self, connection_id: str) -> dict[str, Any]:
        session = self._require_session(connection_id)
        if session.subscribed_config is None:
            raise ProtocolViolationError(
                code="NOT_SUBSCRIBED",
                message="Cannot build FULL_SNAPSHOT before SUBSCRIBED.",
                fatal=True,
            )
        started_run = self._require_started_run(session)
        runner = started_run.runner
        channels = set(session.subscribed_config.effective_channels)
        tick = int(runner.get_tick_index())
        state = self._build_channel_scoped_state(runner=runner, channels=channels)
        canonical_state = canonicalize_state_obj(state)
        step_hash = compute_step_hash(canonical_state)
        return {
            "schema_version": session.run.schema_version,
            "tick": tick,
            "step_hash": step_hash,
            "state": canonical_state,
        }

    def mark_baseline_sent(
        self,
        connection_id: str,
        *,
        tick: int,
        step_hash: str,
        state: dict[str, Any],
    ) -> EnqueteurLiveSession:
        session = self._require_session(connection_id)
        session.baseline_sent = True
        session.baseline_tick = int(tick)
        session.last_tick = int(tick)
        session.last_step_hash = str(step_hash)
        session.last_state = canonicalize_state_obj(state)
        return session

    def advance_runner_and_build_frame_diff_payload(self, connection_id: str) -> dict[str, Any]:
        session = self._require_session(connection_id)
        if session.subscribed_config is None or not session.baseline_sent:
            raise ProtocolViolationError(
                code="NOT_READY_FOR_DIFF",
                message="Cannot stream FRAME_DIFF before SUBSCRIBED baseline delivery.",
                fatal=True,
            )
        if session.last_state is None or session.last_step_hash is None or session.last_tick is None:
            raise ProtocolViolationError(
                code="MISSING_BASELINE",
                message="Live session is missing baseline cursor for FRAME_DIFF streaming.",
                fatal=True,
            )

        started_run = self._require_started_run(session)
        runner = started_run.runner
        channels = set(session.subscribed_config.effective_channels)

        from_tick = int(session.last_tick)
        prev_step_hash = str(session.last_step_hash)

        runner.run(num_ticks=1)
        to_tick = int(runner.get_tick_index())
        if to_tick != from_tick + 1:
            raise ProtocolViolationError(
                code="INVALID_TICK_SEQUENCE",
                message=f"Expected to_tick={from_tick + 1}, got {to_tick}.",
                fatal=True,
            )

        next_state = canonicalize_state_obj(self._build_channel_scoped_state(runner=runner, channels=channels))
        step_hash = compute_step_hash(next_state)
        ops = _compute_enqueteur_frame_diff_ops(
            state_from=session.last_state,
            state_to=next_state,
            channels=channels,
        )

        session.last_tick = to_tick
        session.last_step_hash = step_hash
        session.last_state = next_state

        return {
            "schema_version": session.run.schema_version,
            "from_tick": from_tick,
            "to_tick": to_tick,
            "prev_step_hash": prev_step_hash,
            "step_hash": step_hash,
            "ops": ops,
        }

    def close_connection(
        self,
        connection_id: str,
        *,
        close_code: int = 1000,
        close_reason: str | None = None,
    ) -> EnqueteurLiveSession:
        session = self._sessions.get(connection_id)
        if session is None:
            session = self._closed_sessions.get(connection_id)
            if session is None:
                raise KeyError(f"Unknown connection_id: {connection_id}")
            return session

        session.phase = "CLOSED"
        session.protocol_state = "CLOSED"
        session.closed_at = datetime.now(UTC).isoformat()
        session.close_code = int(close_code)
        session.close_reason = close_reason
        self._sessions.pop(connection_id, None)
        self._closed_sessions[connection_id] = session
        return session

    def cleanup_closed_session(self, connection_id: str) -> EnqueteurLiveSession | None:
        return self._closed_sessions.pop(connection_id, None)

    def get_session(self, connection_id: str) -> EnqueteurLiveSession | None:
        return self._sessions.get(connection_id) or self._closed_sessions.get(connection_id)

    def list_sessions_for_run(self, run_id: str) -> tuple[EnqueteurLiveSession, ...]:
        active = [session for session in self._sessions.values() if session.run.run_id == run_id]
        closed = [session for session in self._closed_sessions.values() if session.run.run_id == run_id]
        return tuple(active + closed)

    def _require_session(self, connection_id: str) -> EnqueteurLiveSession:
        session = self._sessions.get(connection_id)
        if session is None:
            if connection_id in self._closed_sessions:
                raise ProtocolViolationError(
                    code="RUN_ALREADY_CLOSED",
                    message=f"Session {connection_id} is already closed.",
                    fatal=True,
                )
            raise ProtocolViolationError(
                code="RUN_NOT_FOUND",
                message=f"Session {connection_id} is not tracked by this host.",
                fatal=True,
            )
        return session

    def _require_started_run(self, session: EnqueteurLiveSession) -> StartedCaseRun:
        record = self._run_registry.get(session.run.run_id)
        if record is None:
            raise ProtocolViolationError(
                code="RUN_NOT_FOUND",
                message=f"Run {session.run.run_id} is not available for live attachment.",
                fatal=True,
            )
        return record

    def _require_protocol_state(
        self,
        session: EnqueteurLiveSession,
        expected_state: LiveProtocolState,
        *,
        action: str,
    ) -> None:
        if session.protocol_state != expected_state:
            raise ProtocolViolationError(
                code="BAD_SEQUENCE",
                message=(
                    f"{action} received while protocol_state={session.protocol_state}; "
                    f"expected {expected_state}."
                ),
                fatal=True,
            )

    def _build_channel_scoped_state(self, *, runner: Any, channels: set[str]) -> dict[str, Any]:
        case_state = runner.get_case_state()
        progress = runner.get_investigation_progress()
        object_state = runner.get_investigation_object_state()
        dialogue_state = runner.get_dialogue_runtime_state()
        recent_turns = runner.get_dialogue_turn_log()
        evaluation = runner.get_case_outcome_evaluation()

        state: dict[str, Any] = {}

        if "WORLD" in channels:
            world_snapshot = runner.get_world_snapshot()
            state["world"] = {
                "rooms": [asdict(room) for room in world_snapshot.rooms],
                "doors": [asdict(door) for door in world_snapshot.doors],
                "objects": [asdict(obj) for obj in world_snapshot.objects],
                "clock": {
                    "tick": int(world_snapshot.tick_index),
                    "day_index": int(world_snapshot.day_index),
                    "tick_in_day": int(world_snapshot.tick_in_day),
                    "time_of_day": float(world_snapshot.time_of_day),
                    "day_phase": str(world_snapshot.day_phase),
                },
            }

        if "NPCS" in channels:
            npcs = build_visible_npc_semantic_projection(runner.get_npc_states())
            state["npcs"] = {"npcs": npcs}

        if "INVESTIGATION" in channels and case_state is not None and object_state is not None and progress is not None:
            state["investigation"] = build_visible_investigation_projection(
                case_state=case_state,
                object_state=object_state,
                progress=progress,
            )

        if "DIALOGUE" in channels and case_state is not None and dialogue_state is not None and progress is not None:
            dialogue_projection = build_visible_dialogue_projection(
                case_state=case_state,
                runtime_state=dialogue_state,
                progress=progress,
                recent_turns=recent_turns,
            )
            if "LEARNING" not in channels and isinstance(dialogue_projection, dict):
                dialogue_projection.pop("learning", None)
            state["dialogue"] = dialogue_projection

        if "LEARNING" in channels and case_state is not None and dialogue_state is not None and progress is not None:
            state["learning"] = build_visible_learning_projection(
                case_state=case_state,
                runtime_state=dialogue_state,
                progress=progress,
                recent_turns=recent_turns,
            )

        # KVP-ENQ-0001 snapshot shape includes resolution; we scope it to EVENTS.
        if "EVENTS" in channels:
            if evaluation is None:
                state["resolution"] = {
                    "status": "in_progress",
                    "outcome": None,
                    "recap": None,
                }
            else:
                state["resolution"] = {
                    "status": "resolved" if evaluation.terminal else "in_progress",
                    "outcome": build_visible_outcome_projection(evaluation),
                    "recap": build_visible_run_recap_projection(evaluation) if evaluation.terminal else None,
                }

        return state

    def _dispatch_investigate_object(
        self,
        *,
        started_run: StartedCaseRun,
        session: EnqueteurLiveSession,  # noqa: ARG002
        command: ParsedInputCommand,
    ) -> CommandDispatchResult:
        if not isinstance(command.payload, InvestigateObjectCommandPayload):
            return CommandDispatchResult.rejected_result(
                client_cmd_id=command.client_cmd_id,
                reason_code="INVALID_COMMAND",
                message="INVESTIGATE_OBJECT payload shape is invalid after parsing.",
            )

        runner = started_run.runner
        execution = runner.submit_investigation_command(
            make_investigation_command(
                object_id=command.payload.object_id,
                affordance_id=command.payload.action_id,
            )
        )
        if execution is None:
            return CommandDispatchResult.rejected_result(
                client_cmd_id=command.client_cmd_id,
                reason_code="RUNTIME_NOT_READY",
                message="Investigation runtime state is not ready for object commands.",
            )

        ack = execution.ack
        if ack.kind in {"success", "no_op"}:
            return CommandDispatchResult.accepted_result(client_cmd_id=command.client_cmd_id)

        reason_code, message = self._map_investigate_object_rejection(
            object_id=command.payload.object_id,
            action_id=command.payload.action_id,
            ack=ack,
        )
        return CommandDispatchResult.rejected_result(
            client_cmd_id=command.client_cmd_id,
            reason_code=reason_code,
            message=message,
        )

    def _dispatch_dialogue_turn(
        self,
        *,
        started_run: StartedCaseRun,
        session: EnqueteurLiveSession,  # noqa: ARG002
        command: ParsedInputCommand,
    ) -> CommandDispatchResult:
        if not isinstance(command.payload, DialogueTurnCommandPayload):
            return CommandDispatchResult.rejected_result(
                client_cmd_id=command.client_cmd_id,
                reason_code="INVALID_COMMAND",
                message="DIALOGUE_TURN payload shape is invalid after parsing.",
            )

        try:
            request = self._build_dialogue_turn_request(command.payload)
        except ValueError as exc:
            return CommandDispatchResult.rejected_result(
                client_cmd_id=command.client_cmd_id,
                reason_code="INVALID_COMMAND",
                message=f"Invalid DIALOGUE_TURN request: {exc}",
            )

        runner = started_run.runner
        result = runner.submit_dialogue_turn(request)
        if result is None:
            return CommandDispatchResult.rejected_result(
                client_cmd_id=command.client_cmd_id,
                reason_code="RUNTIME_NOT_READY",
                message="Dialogue runtime state is not ready for scene turns.",
            )

        if result.turn_result.status == "accepted":
            return CommandDispatchResult.accepted_result(client_cmd_id=command.client_cmd_id)

        reason_code, message = self._map_dialogue_turn_rejection(result)
        return CommandDispatchResult.rejected_result(
            client_cmd_id=command.client_cmd_id,
            reason_code=reason_code,
            message=message,
        )

    def _dispatch_minigame_submit(
        self,
        *,
        started_run: StartedCaseRun,
        session: EnqueteurLiveSession,  # noqa: ARG002
        command: ParsedInputCommand,
    ) -> CommandDispatchResult:
        if not isinstance(command.payload, MinigameSubmitCommandPayload):
            return CommandDispatchResult.rejected_result(
                client_cmd_id=command.client_cmd_id,
                reason_code="INVALID_COMMAND",
                message="MINIGAME_SUBMIT payload shape is invalid after parsing.",
            )

        canonical_minigame_id = self._canonical_minigame_id(command.payload.minigame_id)
        if canonical_minigame_id is None:
            return CommandDispatchResult.rejected_result(
                client_cmd_id=command.client_cmd_id,
                reason_code="INVALID_COMMAND",
                message=f"Unknown minigame_id '{command.payload.minigame_id}'.",
            )

        expected_target = ENQUETEUR_MINIGAME_TARGETS[canonical_minigame_id]
        if command.payload.target_id != expected_target:
            return CommandDispatchResult.rejected_result(
                client_cmd_id=command.client_cmd_id,
                reason_code="MINIGAME_INVALID_STATE",
                message=(
                    f"Minigame '{canonical_minigame_id}' expects target_id '{expected_target}', "
                    f"got '{command.payload.target_id}'."
                ),
            )

        answer_error = self._validate_minigame_answer_payload(
            minigame_id=canonical_minigame_id,
            answer=command.payload.answer,
        )
        if answer_error is not None:
            return CommandDispatchResult.rejected_result(
                client_cmd_id=command.client_cmd_id,
                reason_code="MINIGAME_INVALID_SUBMISSION",
                message=answer_error,
            )

        action_plan = ENQUETEUR_MINIGAME_ACTION_PLAN[canonical_minigame_id]
        runner = started_run.runner

        for object_id, action_id in action_plan:
            item_context_id = self._resolve_minigame_item_context(
                minigame_id=canonical_minigame_id,
                action_id=action_id,
                answer=command.payload.answer,
            )
            execution = runner.submit_investigation_command(
                make_investigation_command(
                    object_id=object_id,
                    affordance_id=action_id,
                    item_context_id=item_context_id,
                )
            )
            if execution is None:
                return CommandDispatchResult.rejected_result(
                    client_cmd_id=command.client_cmd_id,
                    reason_code="RUNTIME_NOT_READY",
                    message="Minigame runtime state is not ready for submissions.",
                )

            ack = execution.ack
            if ack.kind in {"success", "no_op"}:
                continue

            reason_code, message = self._map_minigame_submit_rejection(
                minigame_id=canonical_minigame_id,
                target_id=command.payload.target_id,
                ack=ack,
            )
            return CommandDispatchResult.rejected_result(
                client_cmd_id=command.client_cmd_id,
                reason_code=reason_code,
                message=message,
            )

        return CommandDispatchResult.accepted_result(client_cmd_id=command.client_cmd_id)

    def _dispatch_attempt_recovery(
        self,
        *,
        started_run: StartedCaseRun,  # noqa: ARG002
        session: EnqueteurLiveSession,  # noqa: ARG002
        command: ParsedInputCommand,
    ) -> CommandDispatchResult:
        return CommandDispatchResult.rejected_result(
            client_cmd_id=command.client_cmd_id,
            reason_code="RUNTIME_NOT_READY",
            message="ATTEMPT_RECOVERY execution is not enabled yet.",
        )

    def _dispatch_attempt_accusation(
        self,
        *,
        started_run: StartedCaseRun,  # noqa: ARG002
        session: EnqueteurLiveSession,  # noqa: ARG002
        command: ParsedInputCommand,
    ) -> CommandDispatchResult:
        return CommandDispatchResult.rejected_result(
            client_cmd_id=command.client_cmd_id,
            reason_code="RUNTIME_NOT_READY",
            message="ATTEMPT_ACCUSATION execution is not enabled yet.",
        )

    def _map_investigate_object_rejection(
        self,
        *,
        object_id: str,
        action_id: str,
        ack: InvestigationCommandAck,
    ) -> tuple[str, str]:
        if ack.code == "unknown_object_id":
            return "INVALID_OBJECT", f"Unknown object_id '{object_id}'."

        if ack.code in {"unknown_affordance_id", "affordance_not_allowed_for_object"}:
            return "OBJECT_ACTION_UNAVAILABLE", (
                f"Action '{action_id}' is not available for object '{object_id}'."
            )

        if ack.kind == "blocked_prerequisite":
            if any(str(token).startswith("scene:") for token in ack.missing_prerequisites):
                return "SCENE_GATE_BLOCKED", (
                    f"Scene gate blocked action '{action_id}' on object '{object_id}'."
                )
            if ack.missing_prerequisites:
                needed = ", ".join(ack.missing_prerequisites)
                return "OBJECT_ACTION_UNAVAILABLE", (
                    f"Action '{action_id}' on object '{object_id}' is blocked by prerequisites: {needed}."
                )
            return "OBJECT_ACTION_UNAVAILABLE", (
                f"Action '{action_id}' on object '{object_id}' is currently unavailable."
            )

        if ack.kind == "state_consumed":
            return "OBJECT_ACTION_UNAVAILABLE", (
                f"Action '{action_id}' on object '{object_id}' has already been consumed."
            )

        if ack.kind == "invalid_action":
            return "INVALID_COMMAND", (
                f"Invalid investigation action '{action_id}' for object '{object_id}' ({ack.code})."
            )

        return "INVALID_COMMAND", (
            f"Unsupported investigation command outcome '{ack.kind}' ({ack.code})."
        )

    def _build_dialogue_turn_request(
        self,
        payload: DialogueTurnCommandPayload,
    ) -> DialogueTurnRequest:
        slot_values: list[DialogueTurnSlotValue] = []
        for slot_name in sorted(payload.slots.keys()):
            value = payload.slots[slot_name]
            if slot_name not in {"time", "location", "item", "person", "reason"}:
                raise ValueError(f"Unsupported slot name '{slot_name}'.")
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Slot '{slot_name}' must be a non-empty string.")
            slot_values.append(
                DialogueTurnSlotValue(slot_name=slot_name, value=value.strip())
            )

        return DialogueTurnRequest(
            scene_id=payload.scene_id,
            npc_id=payload.npc_id,
            intent_id=payload.intent_id,
            provided_slots=tuple(slot_values),
        )

    def _map_dialogue_turn_rejection(self, result: Any) -> tuple[str, str]:
        turn = result.turn_result
        status = str(getattr(turn, "status", ""))
        code = str(getattr(turn, "code", ""))
        scene_id = str(getattr(turn, "scene_id", ""))
        intent_id = str(getattr(turn, "intent_id", ""))
        npc_id = str(getattr(turn, "npc_id", ""))

        if code == "scene_primary_npc_mismatch":
            return "INVALID_NPC", (
                f"NPC '{npc_id}' is not valid for scene '{scene_id}'."
            )

        if code in {"trust_below_threshold"} or code.startswith("insufficient_trust_"):
            return "INSUFFICIENT_TRUST", (
                f"Dialogue turn blocked by trust gate for scene '{scene_id}'."
            )

        if status == "blocked_gate":
            return "SCENE_GATE_BLOCKED", (
                f"Dialogue turn is blocked for scene '{scene_id}' ({code})."
            )

        if code == "missing_required_slots":
            missing = tuple(getattr(turn, "missing_required_slots", ()))
            if missing:
                return "MISSING_REQUIRED_SLOTS", (
                    f"Missing required slots for scene '{scene_id}' intent '{intent_id}': {', '.join(missing)}."
                )
            return "MISSING_REQUIRED_SLOTS", (
                f"Missing required slots for scene '{scene_id}' intent '{intent_id}'."
            )

        if status in {"invalid_intent", "invalid_scene_state"}:
            return "INVALID_COMMAND", (
                f"Dialogue turn is invalid for scene '{scene_id}' and intent '{intent_id}' ({code})."
            )

        if status in {"repair", "refused"}:
            return "SCENE_GATE_BLOCKED", (
                f"Dialogue turn requires correction or was refused ({code})."
            )

        return "INVALID_COMMAND", (
            f"Unsupported dialogue turn outcome '{status}' ({code})."
        )

    def _canonical_minigame_id(self, raw_minigame_id: str) -> str | None:
        normalized = raw_minigame_id.strip().upper()
        return ENQUETEUR_MINIGAME_ID_ALIASES.get(normalized)

    def _validate_minigame_answer_payload(
        self,
        *,
        minigame_id: str,
        answer: dict[str, Any],
    ) -> str | None:
        if not answer:
            return "answer must contain at least one field for MINIGAME_SUBMIT."

        for key, value in answer.items():
            if not isinstance(key, str) or not key.strip():
                return "answer contains an invalid key; keys must be non-empty strings."
            if not self._is_valid_minigame_answer_value(value):
                return (
                    f"answer field '{key}' uses an unsupported value shape for MINIGAME_SUBMIT."
                )

        if minigame_id == "MG2_BADGE_LOG":
            selected = answer.get("selected_entry_id")
            time_value = answer.get("time_value")
            if not isinstance(selected, str) or not selected.strip():
                return "MG2_BADGE_LOG answer requires non-empty selected_entry_id."
            if not isinstance(time_value, str) or not time_value.strip():
                return "MG2_BADGE_LOG answer requires non-empty time_value."

        return None

    def _is_valid_minigame_answer_value(self, value: Any, *, depth: int = 0) -> bool:
        if depth > 3:
            return False
        if isinstance(value, (str, int, float, bool)):
            return True
        if isinstance(value, list):
            return all(self._is_valid_minigame_answer_value(item, depth=depth + 1) for item in value)
        if isinstance(value, dict):
            return all(
                isinstance(key, str)
                and key.strip()
                and self._is_valid_minigame_answer_value(item, depth=depth + 1)
                for key, item in value.items()
            )
        return False

    def _resolve_minigame_item_context(
        self,
        *,
        minigame_id: str,
        action_id: str,
        answer: dict[str, Any],
    ) -> str | None:
        if minigame_id == "MG3_RECEIPT_READING" and action_id == "read_receipt":
            receipt_id = answer.get("receipt_id")
            if isinstance(receipt_id, str) and receipt_id.strip():
                return receipt_id.strip()
        return None

    def _map_minigame_submit_rejection(
        self,
        *,
        minigame_id: str,
        target_id: str,
        ack: InvestigationCommandAck,
    ) -> tuple[str, str]:
        if ack.code in {"unknown_object_id", "unknown_affordance_id", "affordance_not_allowed_for_object"}:
            return "INVALID_COMMAND", (
                f"Minigame '{minigame_id}' is mapped to an unsupported object action."
            )

        if ack.kind in {"blocked_prerequisite", "state_consumed"}:
            return "MINIGAME_INVALID_STATE", (
                f"Minigame '{minigame_id}' is not currently available for target '{target_id}' ({ack.code})."
            )

        if ack.kind == "invalid_action":
            return "INVALID_COMMAND", (
                f"Invalid minigame action mapping for '{minigame_id}' ({ack.code})."
            )

        return "INVALID_COMMAND", (
            f"Unsupported minigame submission outcome '{ack.kind}' ({ack.code})."
        )


_DEFAULT_ENQUETEUR_LIVE_SESSION_HOST = EnqueteurLiveSessionHost()


def get_default_enqueteur_live_session_host() -> EnqueteurLiveSessionHost:
    return _DEFAULT_ENQUETEUR_LIVE_SESSION_HOST


async def open_enqueteur_live_websocket(
    websocket: EnqueteurWebSocketTransport,
    *,
    connection_target: str,
    host: EnqueteurLiveSessionHost | None = None,
) -> EnqueteurLiveSession:
    """Entrypoint for LIVE websocket attach.

    - resolves run_id from connection_target (typically `/live?run_id=...`)
    - attaches connection to a started deterministic run
    - accepts websocket and prepares state machine for VIEWER_HELLO
    """

    session_host = host if host is not None else get_default_enqueteur_live_session_host()
    try:
        session = session_host.attach_connection(connection_target=connection_target)
    except RunLookupError as exc:
        await websocket.accept()
        await _send_error(
            websocket,
            code="RUN_NOT_FOUND",
            message=(
                f"No started run exists for connection target '{exc.connection_target}'."
            ),
            fatal=True,
        )
        await websocket.close(code=RUN_NOT_FOUND_WS_CLOSE_CODE, reason=RUN_NOT_FOUND_WS_CLOSE_REASON)
        raise

    await websocket.accept()
    session_host.mark_handshaking(session.connection_id)
    return session


def handle_enqueteur_live_disconnect(
    *,
    session: EnqueteurLiveSession,
    close_code: int = 1001,
    close_reason: str = "CLIENT_DISCONNECT",
    host: EnqueteurLiveSessionHost | None = None,
) -> EnqueteurLiveSession | None:
    """Finalize session state for a transport disconnect and clean up active maps."""

    session_host = host if host is not None else get_default_enqueteur_live_session_host()
    stored = session_host.get_session(session.connection_id)
    if stored is None:
        return None

    closed = session_host.close_connection(
        session.connection_id,
        close_code=close_code,
        close_reason=close_reason,
    )
    session_host.cleanup_closed_session(session.connection_id)
    return closed


async def handle_enqueteur_live_incoming_message(
    websocket: EnqueteurWebSocketTransport,
    *,
    session: EnqueteurLiveSession,
    raw_message: str | bytes,
    host: EnqueteurLiveSessionHost | None = None,
) -> None:
    """Handle one inbound websocket message using strict KVP envelope dispatch."""

    session_host = host if host is not None else get_default_enqueteur_live_session_host()
    try:
        live_session = session_host.get_session(session.connection_id)
        if live_session is None:
            raise ProtocolViolationError(
                code="RUN_NOT_FOUND",
                message=f"Session {session.connection_id} is not bound to an active run.",
                fatal=True,
            )
        if live_session.phase == "CLOSED":
            raise ProtocolViolationError(
                code="RUN_ALREADY_CLOSED",
                message=f"Session {session.connection_id} is already closed.",
                fatal=True,
            )

        envelope = _decode_incoming_envelope(raw_message)
        msg_type = envelope["msg_type"]
        payload = envelope["payload"]

        if msg_type == "VIEWER_HELLO":
            kernel_hello = session_host.record_viewer_hello(session.connection_id, payload)
            await _send_envelope(websocket, msg_type="KERNEL_HELLO", payload=kernel_hello)
            return

        if msg_type == "SUBSCRIBE":
            subscribed = session_host.record_subscribe(session.connection_id, payload)
            await _send_envelope(websocket, msg_type="SUBSCRIBED", payload=subscribed)
            if subscribed["effective_snapshot_policy"] == "ON_JOIN":
                snapshot = session_host.build_full_snapshot_payload(session.connection_id)
                await _send_envelope(websocket, msg_type="FULL_SNAPSHOT", payload=snapshot)
                session_host.mark_baseline_sent(
                    session.connection_id,
                    tick=int(snapshot["tick"]),
                    step_hash=str(snapshot["step_hash"]),
                    state=dict(snapshot["state"]),
                )
            return

        if msg_type == "PING":
            nonce = payload.get("nonce")
            await _send_envelope(websocket, msg_type="PONG", payload={"nonce": nonce})
            return

        if msg_type == "INPUT_COMMAND":
            if not session_host.can_deliver_state(session.connection_id):
                raise ProtocolViolationError(
                    code="BAD_SEQUENCE",
                    message="INPUT_COMMAND is not allowed before SUBSCRIBED.",
                    fatal=True,
                )

            command = parse_enqueteur_input_command(payload)
            result = session_host.dispatch_input_command(session.connection_id, command)
            if result.accepted:
                await _send_envelope(
                    websocket,
                    msg_type="COMMAND_ACCEPTED",
                    payload={"client_cmd_id": result.client_cmd_id},
                )
                return

            await _send_envelope(
                websocket,
                msg_type="COMMAND_REJECTED",
                payload={
                    "client_cmd_id": result.client_cmd_id,
                    "reason_code": str(result.reason_code),
                    "message": str(result.message),
                },
            )
            return

        if not session_host.can_deliver_state(session.connection_id):
            raise ProtocolViolationError(
                code="BAD_SEQUENCE",
                message=f"{msg_type} is not allowed before SUBSCRIBED.",
                fatal=True,
            )

        await _send_warn(
            websocket,
            code="UNSUPPORTED_MESSAGE",
            message=f"Unsupported msg_type: {msg_type}.",
        )
        return

    except InputCommandValidationError as exc:
        await _send_envelope(
            websocket,
            msg_type="COMMAND_REJECTED",
            payload={
                "client_cmd_id": exc.client_cmd_id,
                "reason_code": exc.reason_code,
                "message": exc.message,
            },
        )
    except ProtocolViolationError as exc:
        await _send_error(websocket, code=exc.code, message=exc.message, fatal=exc.fatal)
        if exc.fatal:
            close_code = PROTOCOL_VIOLATION_WS_CLOSE_CODE
            close_reason = PROTOCOL_VIOLATION_WS_CLOSE_REASON
            if exc.code == "RUN_NOT_FOUND":
                close_code = RUN_NOT_FOUND_WS_CLOSE_CODE
                close_reason = RUN_NOT_FOUND_WS_CLOSE_REASON
            elif exc.code == "INTERNAL_RUNTIME_ERROR":
                close_code = INTERNAL_RUNTIME_WS_CLOSE_CODE
                close_reason = INTERNAL_RUNTIME_WS_CLOSE_REASON
            if session_host.get_session(session.connection_id) is not None:
                session_host.close_connection(
                    session.connection_id,
                    close_code=close_code,
                    close_reason=close_reason,
                )
            await websocket.close(
                code=close_code,
                reason=close_reason,
            )
            if session_host.get_session(session.connection_id) is not None:
                session_host.cleanup_closed_session(session.connection_id)
    except Exception as exc:  # noqa: BLE001
        await _send_error(
            websocket,
            code="INTERNAL_RUNTIME_ERROR",
            message=f"Unhandled internal runtime/session error: {exc}",
            fatal=True,
        )
        if session_host.get_session(session.connection_id) is not None:
            session_host.close_connection(
                session.connection_id,
                close_code=INTERNAL_RUNTIME_WS_CLOSE_CODE,
                close_reason=INTERNAL_RUNTIME_WS_CLOSE_REASON,
            )
        await websocket.close(
            code=INTERNAL_RUNTIME_WS_CLOSE_CODE,
            reason=INTERNAL_RUNTIME_WS_CLOSE_REASON,
        )
        if session_host.get_session(session.connection_id) is not None:
            session_host.cleanup_closed_session(session.connection_id)


async def stream_enqueteur_frame_diff_once(
    websocket: EnqueteurWebSocketTransport,
    *,
    session: EnqueteurLiveSession,
    host: EnqueteurLiveSessionHost | None = None,
) -> dict[str, Any]:
    """Advance one authoritative tick and emit one FRAME_DIFF envelope."""

    session_host = host if host is not None else get_default_enqueteur_live_session_host()
    payload = session_host.advance_runner_and_build_frame_diff_payload(session.connection_id)
    await _send_envelope(websocket, msg_type="FRAME_DIFF", payload=payload)
    return payload


async def stream_enqueteur_frame_diff_loop(
    websocket: EnqueteurWebSocketTransport,
    *,
    session: EnqueteurLiveSession,
    host: EnqueteurLiveSessionHost | None = None,
    max_frames: int | None = None,
    tick_interval_seconds: float = 0.0,
) -> int:
    """Stream FRAME_DIFF envelopes until closed or max_frames reached."""

    session_host = host if host is not None else get_default_enqueteur_live_session_host()
    sent = 0
    while True:
        current = session_host.get_session(session.connection_id)
        if current is None or current.phase == "CLOSED":
            break
        if not session_host.can_deliver_state(session.connection_id):
            break
        if not session_host.can_stream_frame_diff(session.connection_id):
            # The loop only streams post-baseline diffs; ON_JOIN baseline or replay
            # recovery must establish the diff cursor first.
            await _send_warn(
                websocket,
                code="BASELINE_REQUIRED",
                message="FRAME_DIFF streaming is blocked until a baseline cursor is established.",
            )
            break
        if max_frames is not None and sent >= int(max_frames):
            break

        try:
            await stream_enqueteur_frame_diff_once(
                websocket,
                session=session,
                host=session_host,
            )
            sent += 1
        except ProtocolViolationError as exc:
            await _send_error(websocket, code=exc.code, message=exc.message, fatal=exc.fatal)
            if exc.fatal:
                session_host.close_connection(
                    session.connection_id,
                    close_code=PROTOCOL_VIOLATION_WS_CLOSE_CODE,
                    close_reason=PROTOCOL_VIOLATION_WS_CLOSE_REASON,
                )
                await websocket.close(
                    code=PROTOCOL_VIOLATION_WS_CLOSE_CODE,
                    reason=PROTOCOL_VIOLATION_WS_CLOSE_REASON,
                )
                session_host.cleanup_closed_session(session.connection_id)
            break
        except Exception as exc:  # noqa: BLE001
            await _send_error(
                websocket,
                code="INTERNAL_RUNTIME_ERROR",
                message=f"Unhandled internal runtime/session error during FRAME_DIFF: {exc}",
                fatal=True,
            )
            if session_host.get_session(session.connection_id) is not None:
                session_host.close_connection(
                    session.connection_id,
                    close_code=INTERNAL_RUNTIME_WS_CLOSE_CODE,
                    close_reason=INTERNAL_RUNTIME_WS_CLOSE_REASON,
                )
            await websocket.close(
                code=INTERNAL_RUNTIME_WS_CLOSE_CODE,
                reason=INTERNAL_RUNTIME_WS_CLOSE_REASON,
            )
            if session_host.get_session(session.connection_id) is not None:
                session_host.cleanup_closed_session(session.connection_id)
            break

        if tick_interval_seconds > 0:
            await asyncio.sleep(float(tick_interval_seconds))

    return sent


async def _send_envelope(websocket: EnqueteurWebSocketTransport, *, msg_type: str, payload: dict[str, Any]) -> None:
    envelope = make_live_envelope(
        msg_type,
        payload,
        msg_id=str(uuid.uuid4()),
        sent_at_ms=int(datetime.now(UTC).timestamp() * 1000),
    )
    await websocket.send_text(json.dumps(envelope, separators=(",", ":")))


async def _send_error(
    websocket: EnqueteurWebSocketTransport,
    *,
    code: str,
    message: str,
    fatal: bool,
) -> None:
    await _send_envelope(
        websocket,
        msg_type="ERROR",
        payload={
            "code": code,
            "message": message,
            "fatal": bool(fatal),
        },
    )


async def _send_warn(
    websocket: EnqueteurWebSocketTransport,
    *,
    code: str,
    message: str,
) -> None:
    await _send_envelope(
        websocket,
        msg_type="WARN",
        payload={
            "code": code,
            "message": message,
        },
    )


def _decode_incoming_envelope(raw_message: str | bytes) -> dict[str, Any]:
    try:
        text = raw_message.decode("utf-8") if isinstance(raw_message, bytes) else raw_message
        if not isinstance(text, str):
            raise ValueError("Inbound websocket message must be UTF-8 text.")
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("Inbound websocket message must decode to an object envelope.")
        validate_live_envelope(parsed)
        return parsed
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ProtocolViolationError(
            code="PROTOCOL_VIOLATION",
            message=f"Invalid live envelope: {exc}",
            fatal=True,
        ) from exc


def _require_non_empty_str(value: Any, *, field: str, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtocolViolationError(code=code, message=f"{field} must be a non-empty string.", fatal=True)
    return value.strip()


def _require_string_list(
    value: Any,
    *,
    field: str,
    code: str,
    non_empty: bool,
) -> list[str]:
    if not isinstance(value, list):
        raise ProtocolViolationError(code=code, message=f"{field} must be a list.", fatal=True)
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ProtocolViolationError(code=code, message=f"{field} must contain non-empty strings.", fatal=True)
        out.append(item.strip())
    if non_empty and not out:
        raise ProtocolViolationError(code=code, message=f"{field} must be non-empty.", fatal=True)
    return out


def _index_by_id(rows: list[dict[str, Any]], id_field: str) -> dict[Any, dict[str, Any]]:
    indexed: dict[Any, dict[str, Any]] = {}
    for row in rows:
        ident = row.get(id_field)
        if ident is None:
            continue
        indexed[ident] = row
    return indexed


def _append_upsert_remove_ops(
    *,
    ops: list[dict[str, Any]],
    prev_rows: list[dict[str, Any]],
    next_rows: list[dict[str, Any]],
    id_field: str,
    remove_op: str,
    upsert_op: str,
    payload_field: str,
) -> None:
    prev_by_id = _index_by_id(prev_rows, id_field)
    next_by_id = _index_by_id(next_rows, id_field)
    removed = sorted([ident for ident in prev_by_id if ident not in next_by_id])
    changed = sorted(
        [ident for ident in next_by_id if ident not in prev_by_id or next_by_id[ident] != prev_by_id[ident]]
    )

    for ident in removed:
        ops.append({"op": remove_op, id_field: ident})
    for ident in changed:
        ops.append({"op": upsert_op, payload_field: next_by_id[ident]})


def _append_upsert_only_ops(
    *,
    ops: list[dict[str, Any]],
    prev_rows: list[dict[str, Any]],
    next_rows: list[dict[str, Any]],
    id_field: str,
    upsert_op: str,
    payload_field: str,
) -> None:
    prev_by_id = _index_by_id(prev_rows, id_field)
    next_by_id = _index_by_id(next_rows, id_field)
    changed = sorted(
        [ident for ident in next_by_id if ident not in prev_by_id or next_by_id[ident] != prev_by_id[ident]]
    )
    for ident in changed:
        ops.append({"op": upsert_op, payload_field: next_by_id[ident]})


def _append_list_additions(
    *,
    ops: list[dict[str, Any]],
    prev_values: list[str],
    next_values: list[str],
    op: str,
    field: str,
) -> None:
    prev_set = set(prev_values)
    for value in sorted([v for v in next_values if v not in prev_set]):
        ops.append({"op": op, field: value})


def _append_list_removals(
    *,
    ops: list[dict[str, Any]],
    prev_values: list[str],
    next_values: list[str],
    op: str,
    field: str,
) -> None:
    next_set = set(next_values)
    for value in sorted([v for v in prev_values if v not in next_set]):
        ops.append({"op": op, field: value})


def _append_dialogue_turn_ops(
    *,
    ops: list[dict[str, Any]],
    prev_turns: list[dict[str, Any]],
    next_turns: list[dict[str, Any]],
) -> None:
    prev_indices = {int(turn.get("turn_index")) for turn in prev_turns if isinstance(turn.get("turn_index"), int)}
    new_turns = [
        turn for turn in next_turns
        if isinstance(turn.get("turn_index"), int) and int(turn["turn_index"]) not in prev_indices
    ]
    for turn in sorted(new_turns, key=lambda row: int(row["turn_index"])):
        ops.append({"op": "APPEND_DIALOGUE_TURN", "turn": turn})


def _append_learning_outcome_ops(
    *,
    ops: list[dict[str, Any]],
    prev_rows: list[dict[str, Any]],
    next_rows: list[dict[str, Any]],
) -> None:
    if not next_rows:
        return
    start_idx = 0
    if len(prev_rows) <= len(next_rows) and next_rows[:len(prev_rows)] == prev_rows:
        start_idx = len(prev_rows)
    for row in next_rows[start_idx:]:
        ops.append({"op": "APPEND_LEARNING_OUTCOME", "outcome": row})


def _compute_enqueteur_frame_diff_ops(
    *,
    state_from: dict[str, Any],
    state_to: dict[str, Any],
    channels: set[str],
) -> list[dict[str, Any]]:
    ops: list[dict[str, Any]] = []

    if "WORLD" in channels:
        prev_world = state_from.get("world") if isinstance(state_from.get("world"), dict) else {}
        next_world = state_to.get("world") if isinstance(state_to.get("world"), dict) else {}
        _append_upsert_remove_ops(
            ops=ops,
            prev_rows=list(prev_world.get("rooms", [])),
            next_rows=list(next_world.get("rooms", [])),
            id_field="room_id",
            remove_op="REMOVE_ROOM",
            upsert_op="UPSERT_ROOM",
            payload_field="room",
        )
        _append_upsert_remove_ops(
            ops=ops,
            prev_rows=list(prev_world.get("doors", [])),
            next_rows=list(next_world.get("doors", [])),
            id_field="door_id",
            remove_op="REMOVE_DOOR",
            upsert_op="UPSERT_DOOR",
            payload_field="door",
        )
        _append_upsert_remove_ops(
            ops=ops,
            prev_rows=list(prev_world.get("objects", [])),
            next_rows=list(next_world.get("objects", [])),
            id_field="object_id",
            remove_op="REMOVE_OBJECT",
            upsert_op="UPSERT_OBJECT",
            payload_field="object",
        )
        if prev_world.get("clock") != next_world.get("clock"):
            ops.append({"op": "SET_CLOCK", "clock": next_world.get("clock")})

    if "NPCS" in channels:
        prev_npcs = state_from.get("npcs") if isinstance(state_from.get("npcs"), dict) else {}
        next_npcs = state_to.get("npcs") if isinstance(state_to.get("npcs"), dict) else {}
        _append_upsert_remove_ops(
            ops=ops,
            prev_rows=list(prev_npcs.get("npcs", [])),
            next_rows=list(next_npcs.get("npcs", [])),
            id_field="npc_id",
            remove_op="REMOVE_NPC",
            upsert_op="UPSERT_NPC",
            payload_field="npc",
        )

    if "INVESTIGATION" in channels:
        prev_inv = state_from.get("investigation") if isinstance(state_from.get("investigation"), dict) else {}
        next_inv = state_to.get("investigation") if isinstance(state_to.get("investigation"), dict) else {}
        prev_evidence = prev_inv.get("evidence") if isinstance(prev_inv.get("evidence"), dict) else {}
        next_evidence = next_inv.get("evidence") if isinstance(next_inv.get("evidence"), dict) else {}
        prev_facts = prev_inv.get("facts") if isinstance(prev_inv.get("facts"), dict) else {}
        next_facts = next_inv.get("facts") if isinstance(next_inv.get("facts"), dict) else {}
        prev_contra = prev_inv.get("contradictions") if isinstance(prev_inv.get("contradictions"), dict) else {}
        next_contra = next_inv.get("contradictions") if isinstance(next_inv.get("contradictions"), dict) else {}

        _append_list_additions(
            ops=ops,
            prev_values=list(prev_evidence.get("discovered_ids", [])),
            next_values=list(next_evidence.get("discovered_ids", [])),
            op="REVEAL_EVIDENCE",
            field="evidence_id",
        )
        _append_list_additions(
            ops=ops,
            prev_values=list(prev_evidence.get("collected_ids", [])),
            next_values=list(next_evidence.get("collected_ids", [])),
            op="COLLECT_EVIDENCE",
            field="evidence_id",
        )
        _append_upsert_only_ops(
            ops=ops,
            prev_rows=list(prev_inv.get("objects", [])),
            next_rows=list(next_inv.get("objects", [])),
            id_field="object_id",
            upsert_op="SET_OBJECT_INVESTIGATION_STATE",
            payload_field="object_state",
        )
        _append_list_additions(
            ops=ops,
            prev_values=list(prev_facts.get("known_fact_ids", [])),
            next_values=list(next_facts.get("known_fact_ids", [])),
            op="REVEAL_FACT",
            field="fact_id",
        )
        _append_list_additions(
            ops=ops,
            prev_values=list(prev_contra.get("unlockable_edge_ids", [])),
            next_values=list(next_contra.get("unlockable_edge_ids", [])),
            op="MAKE_CONTRADICTION_AVAILABLE",
            field="contradiction_id",
        )
        _append_list_removals(
            ops=ops,
            prev_values=list(prev_contra.get("unlockable_edge_ids", [])),
            next_values=list(next_contra.get("unlockable_edge_ids", [])),
            op="CLEAR_CONTRADICTION_AVAILABLE",
            field="contradiction_id",
        )

    if "DIALOGUE" in channels:
        prev_dialogue = state_from.get("dialogue") if isinstance(state_from.get("dialogue"), dict) else {}
        next_dialogue = state_to.get("dialogue") if isinstance(state_to.get("dialogue"), dict) else {}
        if prev_dialogue.get("active_scene_id") != next_dialogue.get("active_scene_id"):
            ops.append({"op": "SET_ACTIVE_SCENE", "scene_id": next_dialogue.get("active_scene_id")})
        _append_upsert_only_ops(
            ops=ops,
            prev_rows=list(prev_dialogue.get("scene_completion", [])),
            next_rows=list(next_dialogue.get("scene_completion", [])),
            id_field="scene_id",
            upsert_op="UPSERT_SCENE_STATE",
            payload_field="scene_state",
        )
        _append_dialogue_turn_ops(
            ops=ops,
            prev_turns=list(prev_dialogue.get("recent_turns", [])),
            next_turns=list(next_dialogue.get("recent_turns", [])),
        )

    if "LEARNING" in channels:
        prev_learning = state_from.get("learning") if isinstance(state_from.get("learning"), dict) else {}
        next_learning = state_to.get("learning") if isinstance(state_to.get("learning"), dict) else {}
        if prev_learning.get("current_hint_level") != next_learning.get("current_hint_level"):
            ops.append({"op": "SET_HINT_LEVEL", "hint_level": next_learning.get("current_hint_level")})
        _append_upsert_only_ops(
            ops=ops,
            prev_rows=list(prev_learning.get("minigames", [])),
            next_rows=list(next_learning.get("minigames", [])),
            id_field="minigame_id",
            upsert_op="UPSERT_MINIGAME_STATE",
            payload_field="minigame_state",
        )
        prev_summary_state = {
            "summary_by_scene": prev_learning.get("summary_by_scene"),
            "scaffolding_policy": prev_learning.get("scaffolding_policy"),
        }
        next_summary_state = {
            "summary_by_scene": next_learning.get("summary_by_scene"),
            "scaffolding_policy": next_learning.get("scaffolding_policy"),
        }
        if prev_summary_state != next_summary_state:
            ops.append({"op": "SET_SUMMARY_STATE", "summary_state": next_summary_state})
        _append_learning_outcome_ops(
            ops=ops,
            prev_rows=list(prev_learning.get("recent_outcomes", [])),
            next_rows=list(next_learning.get("recent_outcomes", [])),
        )

    if "EVENTS" in channels:
        prev_resolution = state_from.get("resolution") if isinstance(state_from.get("resolution"), dict) else {}
        next_resolution = state_to.get("resolution") if isinstance(state_to.get("resolution"), dict) else {}
        if prev_resolution.get("status") != next_resolution.get("status"):
            ops.append({"op": "SET_RESOLUTION_STATUS", "status": next_resolution.get("status")})
        if prev_resolution.get("outcome") != next_resolution.get("outcome"):
            ops.append({"op": "SET_OUTCOME", "outcome": next_resolution.get("outcome")})
        if prev_resolution.get("recap") != next_resolution.get("recap"):
            ops.append({"op": "SET_RECAP", "recap": next_resolution.get("recap")})

    return ops


__all__ = [
    "ENQUETEUR_LIVE_WS_PATH",
    "RUN_NOT_FOUND_WS_CLOSE_CODE",
    "RUN_NOT_FOUND_WS_CLOSE_REASON",
    "PROTOCOL_VIOLATION_WS_CLOSE_CODE",
    "PROTOCOL_VIOLATION_WS_CLOSE_REASON",
    "INTERNAL_RUNTIME_WS_CLOSE_CODE",
    "INTERNAL_RUNTIME_WS_CLOSE_REASON",
    "ENQUETEUR_ALLOWED_CHANNELS",
    "LiveProtocolPhase",
    "LiveProtocolState",
    "EnqueteurWebSocketTransport",
    "RunLookupError",
    "ProtocolViolationError",
    "EnqueteurViewerHello",
    "EnqueteurSubscribedConfig",
    "EnqueteurRunBinding",
    "EnqueteurLiveSession",
    "EnqueteurLiveSessionHost",
    "get_default_enqueteur_live_session_host",
    "open_enqueteur_live_websocket",
    "handle_enqueteur_live_disconnect",
    "handle_enqueteur_live_incoming_message",
    "stream_enqueteur_frame_diff_once",
    "stream_enqueteur_frame_diff_loop",
]
