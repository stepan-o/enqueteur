from __future__ import annotations

"""LIVE session host for sim_sim schema sim_sim_1."""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Sequence

from backend.sim4.host.kvp_defaults import default_render_spec
from backend.sim4.integration.live_envelope import validate_live_envelope
from backend.sim4.integration.live_session import LiveSession
from backend.sim4.integration.manifest_schema import ALLOWED_CHANNELS
from backend.sim4.integration.render_spec import Bounds

from backend.sim_sim.kernel.state import (
    DayInput,
    EndOfDayActions,
    PromptResponse,
    ROOM_IDS,
    SimSimKernel,
    SimSimState,
    format_state_for_cli,
    resolve_supervisor_code,
)
from backend.sim_sim.projection.kvp_schema1 import (
    SIM_SIM_SCHEMA_VERSION,
    compute_step_hash_for_channels,
    make_diff_payload,
    make_snapshot_payload,
    normalize_channels,
)

logger = logging.getLogger(__name__)

ALLOWED_INBOUND_MSG_TYPES = {"VIEWER_HELLO", "SUBSCRIBE", "PING", "SIM_INPUT"}


@dataclass(frozen=True)
class SimSimRunAnchors:
    engine_name: str
    engine_version: str
    schema_version: str
    world_id: str
    run_id: str
    seed: int
    tick_rate_hz: int
    time_origin_ms: int


class JsonLiveCodec:
    """Simple JSON bytes codec for LiveSession transport."""

    def encode(self, envelope: Dict[str, Any]) -> bytes:
        validate_live_envelope(envelope)
        return json.dumps(envelope, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def decode(self, data: bytes) -> Dict[str, Any]:
        text = data.decode("utf-8")
        obj = json.loads(text)
        if not isinstance(obj, dict):
            raise ValueError("Envelope must decode to object")
        return obj


class AsyncTransportAdapter:
    """Bridge LiveSession sync transport into async websocket send function."""

    def __init__(self, send_bytes: Callable[[bytes], Awaitable[None]]) -> None:
        self._send_bytes = send_bytes
        self._loop = asyncio.get_running_loop()
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._sender_task = self._loop.create_task(self._sender_loop())

    def send(self, data: bytes) -> None:
        self._queue.put_nowait(data)

    async def close(self) -> None:
        self._sender_task.cancel()
        try:
            await self._sender_task
        except asyncio.CancelledError:
            pass

    async def _sender_loop(self) -> None:
        try:
            while True:
                data = await self._queue.get()
                try:
                    await self._send_bytes(data)
                except Exception:
                    logger.exception("Failed to send LIVE envelope")
        except asyncio.CancelledError:
            pass


@dataclass
class ConnectionContext:
    connection_id: str
    session: LiveSession
    transport: AsyncTransportAdapter
    codec: JsonLiveCodec
    send_bytes: Callable[[bytes], Awaitable[None]]
    effective_channels: List[str] = field(default_factory=lambda: list(ALLOWED_CHANNELS))
    snapshot_policy: str = "ON_JOIN"
    last_tick: int | None = None
    last_step_hash: str | None = None


class SessionHost:
    """Owns sim_sim state and all LIVE sessions."""

    def __init__(self, *, seed: int, config_path: str | None = None) -> None:
        self._kernel = SimSimKernel(seed=seed, config_path=config_path)
        self._pending_inputs: Dict[int, DayInput] = {}
        self._connections: Dict[str, ConnectionContext] = {}
        self._lock = asyncio.Lock()

        self._run_anchors = SimSimRunAnchors(
            engine_name="sim_sim",
            engine_version="0.1.0",
            schema_version=SIM_SIM_SCHEMA_VERSION,
            world_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4()),
            seed=int(seed),
            tick_rate_hz=1,
            time_origin_ms=0,
        )
        self._projection_run_context = {
            "seed": int(self._run_anchors.seed),
            "run_id": str(self._run_anchors.run_id),
            "world_id": str(self._run_anchors.world_id),
            "tick_hz": int(self._run_anchors.tick_rate_hz),
            "config_hash": str(self._kernel.loaded_config.config_hash),
            "config_id": str(self._kernel.loaded_config.config_id),
        }
        self._render_spec = default_render_spec(
            bounds=Bounds(min_x=0.0, min_y=0.0, max_x=36.0, max_y=16.0),
            units_per_tile=1.0,
        )
        logger.info(
            "[kernel] sim_sim boot seed=%s config_id=%s config_hash=%s",
            seed,
            self._kernel.loaded_config.config_id,
            self._kernel.loaded_config.config_hash,
        )

    @property
    def current_tick(self) -> int:
        return int(self._kernel.state.day_tick)

    @property
    def current_state(self) -> SimSimState:
        return self._kernel.state

    def describe_state(self) -> str:
        return format_state_for_cli(self._kernel.state)

    async def register_connection(
        self,
        *,
        send_bytes: Callable[[bytes], Awaitable[None]],
    ) -> ConnectionContext:
        async with self._lock:
            codec = JsonLiveCodec()
            transport = AsyncTransportAdapter(send_bytes)
            session = LiveSession(
                transport=transport,
                codec=codec,
                run_anchors=self._run_anchors,
                render_spec=self._render_spec,
            )
            connection_id = str(uuid.uuid4())
            ctx = ConnectionContext(
                connection_id=connection_id,
                session=session,
                transport=transport,
                codec=codec,
                send_bytes=send_bytes,
            )
            self._connections[connection_id] = ctx
            logger.info("[live] connection opened id=%s", connection_id)
            return ctx

    async def unregister_connection(self, ctx: ConnectionContext) -> None:
        async with self._lock:
            self._connections.pop(ctx.connection_id, None)
            await ctx.transport.close()
            logger.info("[live] connection closed id=%s", ctx.connection_id)

    async def handle_client_message(self, ctx: ConnectionContext, raw_data: bytes) -> None:
        try:
            envelope = ctx.codec.decode(raw_data)
        except Exception:
            await self._record_input_ack_event(
                accepted=False,
                reason_code="INVALID_ENVELOPE",
                reason="unable to decode envelope as JSON object",
                source=f"ws:{ctx.connection_id}",
                tick_target=self.current_tick + 1,
            )
            await self._broadcast_current_snapshot()
            logger.info("[live] rejected inbound envelope id=%s reason=INVALID_ENVELOPE", ctx.connection_id)
            return

        msg_type = str(envelope.get("msg_type", ""))

        try:
            validate_live_envelope(envelope)
        except Exception as exc:
            reason_code = "UNSUPPORTED_MSG_TYPE" if msg_type and msg_type not in ALLOWED_INBOUND_MSG_TYPES else "INVALID_ENVELOPE"
            await self._record_input_ack_event(
                accepted=False,
                reason_code=reason_code,
                reason=str(exc),
                source=f"ws:{ctx.connection_id}",
                tick_target=self.current_tick + 1,
                msg_type=msg_type or None,
            )
            await self._broadcast_current_snapshot()
            logger.info(
                "[live] rejected inbound envelope id=%s msg_type=%s reason_code=%s",
                ctx.connection_id,
                msg_type or "UNKNOWN",
                reason_code,
            )
            return

        if msg_type == "SIM_INPUT":
            await self._handle_sim_input(ctx, envelope)
            return

        if msg_type not in ALLOWED_INBOUND_MSG_TYPES:
            await self._record_input_ack_event(
                accepted=False,
                reason_code="UNSUPPORTED_MSG_TYPE",
                reason=f"unsupported inbound msg_type={msg_type}",
                source=f"ws:{ctx.connection_id}",
                tick_target=self.current_tick + 1,
                msg_type=msg_type,
            )
            await self._broadcast_current_snapshot()
            logger.info("[live] rejected msg_type=%s id=%s", msg_type, ctx.connection_id)
            return

        # Envelope-first dispatch: hand protocol messages to LiveSession by msg_type.
        ctx.session.handle_incoming(raw_data)

        if msg_type == "SUBSCRIBE":
            payload = envelope.get("payload", {})
            if isinstance(payload, dict):
                ctx.snapshot_policy = str(payload.get("snapshot_policy", "ON_JOIN"))
            effective = list(getattr(ctx.session, "_effective_channels", []))
            if effective:
                ctx.effective_channels = normalize_channels(effective)
            if bool(getattr(ctx.session, "_subscribed", False)):
                logger.info(
                    "[live] subscribed id=%s channels=%s snapshot_policy=%s",
                    ctx.connection_id,
                    ",".join(ctx.effective_channels),
                    ctx.snapshot_policy,
                )
                await self._send_on_join_baseline_if_needed(ctx)

    async def submit_day_input(
        self,
        day_input: DayInput,
        *,
        source: str,
    ) -> tuple[bool, str]:
        async with self._lock:
            expected_tick = self.current_tick + 1
            valid, reason = self._kernel.validate_day_input(day_input, expected_tick_target=expected_tick)
            if not valid:
                return False, reason
            if self._kernel.state.phase == "awaiting_prompts":
                # Prompt responses are applied immediately via advance_day fallback.
                self._pending_inputs.pop(day_input.tick_target, None)
                logger.info("[input] accepted source=%s tick_target=%s (awaiting_prompts immediate mode)", source, day_input.tick_target)
                return True, "accepted"
            if day_input.tick_target in self._pending_inputs:
                return False, f"day input already queued for tick {day_input.tick_target}"
            self._pending_inputs[day_input.tick_target] = day_input
            logger.info("[input] accepted source=%s tick_target=%s", source, day_input.tick_target)
            return True, "accepted"

    async def advance_day(self, fallback_input: DayInput) -> tuple[int, DayInput]:
        async with self._lock:
            next_tick = self.current_tick + 1
            if self._kernel.state.phase == "awaiting_prompts":
                # Never let stale queued next-tick input shadow prompt responses.
                self._pending_inputs.pop(next_tick, None)
                selected_input = fallback_input
            else:
                selected_input = self._pending_inputs.pop(next_tick, fallback_input)
            valid, reason = self._kernel.validate_day_input(selected_input, expected_tick_target=next_tick)
            if not valid:
                raise ValueError(reason)

            previous, current = self._kernel.step(selected_input)
            from_tick = int(previous.day_tick)
            to_tick = int(current.day_tick)
            logger.info("[kernel] advanced from=%s to=%s", from_tick, to_tick)

            for conn in list(self._connections.values()):
                await self._publish_day_transition(conn, previous, current)
            return to_tick, selected_input

    async def _send_on_join_baseline_if_needed(self, ctx: ConnectionContext) -> None:
        if ctx.snapshot_policy != "ON_JOIN":
            return
        if bool(getattr(ctx.session, "_baseline_sent", False)):
            return
        await self._send_snapshot(ctx, self._kernel.state, tick=self.current_tick)

    async def _send_snapshot(self, ctx: ConnectionContext, domain_state: SimSimState, *, tick: int) -> None:
        channels = normalize_channels(ctx.effective_channels)
        payload = make_snapshot_payload(
            tick=tick,
            domain_state=domain_state,
            channels=channels,
            run_context=self._projection_run_context,
        )
        ctx.session.publish_full_snapshot(payload)
        ctx.last_tick = int(tick)
        ctx.last_step_hash = str(payload["step_hash"])
        logger.info("[live] snapshot id=%s tick=%s", ctx.connection_id, tick)

    async def _publish_day_transition(
        self,
        ctx: ConnectionContext,
        previous_state: SimSimState,
        current_state: SimSimState,
    ) -> None:
        if not bool(getattr(ctx.session, "_subscribed", False)):
            return

        from_tick = int(previous_state.day_tick)
        to_tick = int(current_state.day_tick)

        if ctx.snapshot_policy == "ON_JOIN" and not bool(getattr(ctx.session, "_baseline_sent", False)):
            await self._send_snapshot(ctx, previous_state, tick=from_tick)

        if ctx.last_tick != from_tick:
            # If the connection drifted, reset with authoritative baseline first.
            await self._send_snapshot(ctx, previous_state, tick=from_tick)

        if to_tick == from_tick:
            # Deferred prompt resolution path: state changed at same tick, so emit a fresh snapshot.
            await self._send_snapshot(ctx, current_state, tick=to_tick)
            logger.info("[live] snapshot id=%s tick=%s (same-tick state update)", ctx.connection_id, to_tick)
            return

        channels = normalize_channels(ctx.effective_channels)
        prev_hash = ctx.last_step_hash or compute_step_hash_for_channels(
            previous_state,
            channels,
            run_context=self._projection_run_context,
        )
        payload = make_diff_payload(
            from_tick=from_tick,
            to_tick=to_tick,
            previous_state=previous_state,
            next_state=current_state,
            prev_step_hash=prev_hash,
            channels=channels,
            run_context=self._projection_run_context,
        )
        ctx.session.publish_frame_diff(payload)
        ctx.last_tick = to_tick
        ctx.last_step_hash = str(payload["step_hash"])
        logger.info("[live] diff id=%s from=%s to=%s", ctx.connection_id, from_tick, to_tick)

    async def _handle_sim_input(self, ctx: ConnectionContext, envelope: Mapping[str, Any]) -> None:
        msg_type = str(envelope.get("msg_type", ""))
        phase_before = str(self.current_state.phase)
        parsed = self._parse_sim_input_envelope(envelope)
        if parsed[0] is None:
            reason_code = parsed[1]
            reason = parsed[2]
            await self._record_input_ack_event(
                accepted=False,
                reason_code=reason_code,
                reason=reason,
                source=f"ws:{ctx.connection_id}",
                tick_target=self.current_tick + 1,
                msg_type=msg_type,
            )
            await self._broadcast_current_snapshot()
            logger.info("[input] rejected source=ws:%s reason_code=%s reason=%s", ctx.connection_id, reason_code, reason)
            return

        day_input = parsed[0]
        accepted, reason = await self.submit_day_input(day_input, source=f"ws:{ctx.connection_id}")
        rejection_reason_code = self._kernel_reason_code(reason)
        await self._record_input_ack_event(
            accepted=accepted,
            reason_code="INPUT_ACCEPTED" if accepted else rejection_reason_code,
            reason=reason,
            source=f"ws:{ctx.connection_id}",
            tick_target=day_input.tick_target,
            msg_type=msg_type,
        )
        if accepted and phase_before == "awaiting_prompts":
            await self.advance_day(day_input)
        else:
            await self._broadcast_current_snapshot()
        logger.info(
            "[input] %s source=ws:%s msg_type=%s tick_target=%s reason_code=%s reason=%s",
            "accepted" if accepted else "rejected",
            ctx.connection_id,
            msg_type,
            day_input.tick_target,
            "INPUT_ACCEPTED" if accepted else rejection_reason_code,
            reason,
        )

    def _kernel_reason_code(self, reason: str) -> str:
        text = str(reason)
        if text.startswith("SUPERVISOR_SWAP_BUDGET_EXCEEDED"):
            return "SUPERVISOR_SWAP_BUDGET_EXCEEDED"
        return "KERNEL_VALIDATION_FAILED"

    def _parse_sim_input_envelope(self, envelope: Mapping[str, Any]) -> tuple[DayInput | None, str, str]:
        msg_type = str(envelope.get("msg_type", ""))
        if msg_type != "SIM_INPUT":
            return None, "UNSUPPORTED_MSG_TYPE", f"unsupported input msg_type={msg_type}"

        next_tick = self.current_tick + 1
        tick_target: int = next_tick
        set_supervisors: Dict[int, str | None] = {}
        end_of_day = EndOfDayActions()
        prompt_responses: List[PromptResponse] = []

        payload_obj = envelope.get("payload", {})
        if not isinstance(payload_obj, dict):
            return None, "INVALID_PAYLOAD", "payload must be an object"

        # Support both direct payload shape and wrapped payload shape:
        # direct: {tick_target,set_supervisors,end_of_day,prompt_responses}
        # wrapped: {schema,tick_target,payload:{...}}
        command_payload = payload_obj
        if "payload" in payload_obj:
            allowed_wrapper_keys = {"schema", "tick_target", "payload"}
            unknown_wrapper_keys = [k for k in payload_obj.keys() if k not in allowed_wrapper_keys]
            if unknown_wrapper_keys:
                return None, "INVALID_PAYLOAD", f"unsupported SIM_INPUT wrapper key(s): {','.join(sorted(str(k) for k in unknown_wrapper_keys))}"
            schema = payload_obj.get("schema")
            if schema is not None and str(schema) != SIM_SIM_SCHEMA_VERSION:
                return None, "INVALID_SCHEMA", f"schema must be {SIM_SIM_SCHEMA_VERSION}"
            nested_payload = payload_obj.get("payload")
            if not isinstance(nested_payload, dict):
                return None, "INVALID_PAYLOAD", "SIM_INPUT.payload must be an object"
            command_payload = nested_payload

        allowed_payload_keys = {"tick_target", "set_supervisors", "set_workers", "end_of_day", "prompt_responses"}
        unknown_payload_keys = [k for k in command_payload.keys() if k not in allowed_payload_keys]
        if unknown_payload_keys:
            return None, "INVALID_PAYLOAD", f"unsupported SIM_INPUT payload key(s): {','.join(sorted(str(k) for k in unknown_payload_keys))}"

        tick_raw = None
        if "tick_target" in payload_obj:
            tick_raw = payload_obj.get("tick_target")
        elif "tick_target" in command_payload:
            tick_raw = command_payload.get("tick_target")

        if tick_raw is not None:
            if not isinstance(tick_raw, int):
                return None, "INVALID_TICK_TARGET", "tick_target must be an integer"
            if tick_raw != next_tick:
                return None, "INVALID_TICK_TARGET", f"tick_target must equal next day tick ({next_tick})"
            tick_target = int(tick_raw)

        if "set_workers" in command_payload:
            return None, "DISALLOWED_FIELD_SET_WORKERS", "set_workers is not supported by sim_sim LIVE contract"

        is_awaiting_prompts = self.current_state.phase == "awaiting_prompts"
        if is_awaiting_prompts:
            disallowed_keys = [key for key in ("set_supervisors", "end_of_day") if key in command_payload]
            if disallowed_keys:
                return (
                    None,
                    "AWAITING_PROMPTS_DISALLOWED_FIELDS_PRESENT",
                    f"while awaiting prompts, SIM_INPUT may include only prompt_responses (found: {','.join(disallowed_keys)})",
                )
            if "prompt_responses" not in command_payload:
                return None, "AWAITING_PROMPTS_PROMPT_RESPONSES_REQUIRED", "while awaiting prompts, prompt_responses are required"
        else:
            if "prompt_responses" in command_payload:
                return (
                    None,
                    "DISALLOWED_FIELD_PROMPT_RESPONSES_IN_PLANNING",
                    "prompt_responses are only accepted while phase=awaiting_prompts",
                )

        if not is_awaiting_prompts:
            raw_sup = command_payload.get("set_supervisors", {})
            if not isinstance(raw_sup, dict):
                return None, "INVALID_SET_SUPERVISORS", "set_supervisors must be an object"
            for room_raw, code_raw in raw_sup.items():
                try:
                    room_id = int(room_raw)
                except Exception:
                    return None, "INVALID_SET_SUPERVISORS", "set_supervisors keys must be integer room ids"
                if room_id not in ROOM_IDS:
                    return None, "INVALID_SET_SUPERVISORS", f"set_supervisors includes invalid room_id={room_id}"
                if code_raw is None:
                    set_supervisors[room_id] = None
                    continue
                if not isinstance(code_raw, str):
                    return None, "INVALID_SET_SUPERVISORS", f"set_supervisors[{room_id}] must be supervisor code string or null"
                parsed_code = resolve_supervisor_code(code_raw)
                if parsed_code is None:
                    return None, "INVALID_SET_SUPERVISORS", f"unknown supervisor code for room {room_id}"
                set_supervisors[room_id] = parsed_code

            raw_eod = command_payload.get("end_of_day", {})
            if not isinstance(raw_eod, dict):
                return None, "INVALID_END_OF_DAY", "end_of_day must be an object"
            allowed_eod_keys = {
                "sell_washed_dumb",
                "sell_washed_smart",
                "convert_workers_dumb",
                "convert_workers_smart",
                "upgrade_brains",
            }
            unknown_eod_keys = [k for k in raw_eod.keys() if k not in allowed_eod_keys]
            if unknown_eod_keys:
                return None, "INVALID_END_OF_DAY", f"end_of_day has unsupported key(s): {','.join(sorted(str(k) for k in unknown_eod_keys))}"
            eod_values: Dict[str, int] = {}
            for key in allowed_eod_keys:
                value = raw_eod.get(key, 0)
                if not isinstance(value, int) or value < 0:
                    return None, "INVALID_END_OF_DAY", f"end_of_day.{key} must be a non-negative integer"
                eod_values[key] = int(value)
            end_of_day = EndOfDayActions(
                sell_washed_dumb=eod_values["sell_washed_dumb"],
                sell_washed_smart=eod_values["sell_washed_smart"],
                convert_workers_dumb=eod_values["convert_workers_dumb"],
                convert_workers_smart=eod_values["convert_workers_smart"],
                upgrade_brains=eod_values["upgrade_brains"],
            )

        prompt_by_id = {
            prompt.prompt_id: set(str(choice) for choice in prompt.choices)
            for prompt in self.current_state.prompts
        }
        seen_prompt_ids: set[str] = set()
        raw_prompts = command_payload.get("prompt_responses", [])
        rows: List[Dict[str, Any]] = []
        if isinstance(raw_prompts, dict):
            for prompt_id_key, choice_value in raw_prompts.items():
                rows.append({"prompt_id": prompt_id_key, "choice": choice_value})
        elif isinstance(raw_prompts, list):
            for row in raw_prompts:
                if not isinstance(row, dict):
                    return None, "INVALID_PROMPT_RESPONSES", "prompt_responses entries must be objects"
                rows.append(dict(row))
        else:
            return None, "INVALID_PROMPT_RESPONSES", "prompt_responses must be an object or array"

        for row in rows:
            if set(row.keys()) != {"prompt_id", "choice"}:
                return None, "INVALID_PROMPT_RESPONSES", "prompt_responses entries must include only prompt_id and choice"
            prompt_id = row.get("prompt_id")
            choice = row.get("choice")
            if not isinstance(prompt_id, str) or not prompt_id.strip():
                return None, "INVALID_PROMPT_RESPONSES", "prompt_responses.prompt_id must be a non-empty string"
            if not isinstance(choice, str) or not choice.strip():
                return None, "INVALID_PROMPT_RESPONSES", "prompt_responses.choice must be a non-empty string"
            if prompt_id in seen_prompt_ids:
                return None, "INVALID_PROMPT_RESPONSES", f"duplicate prompt response for prompt_id={prompt_id}"
            seen_prompt_ids.add(prompt_id)
            allowed_choices = prompt_by_id.get(prompt_id)
            if allowed_choices is None:
                return None, "PROMPT_ID_UNKNOWN", f"unknown prompt_id={prompt_id}"
            if choice not in allowed_choices:
                return None, "PROMPT_CHOICE_INVALID", f"invalid choice for prompt_id={prompt_id}"
            prompt_responses.append(PromptResponse(prompt_id=prompt_id, choice=choice))

        return (
            DayInput(
                tick_target=int(tick_target),
                advance=True,
                supervisor_swaps=tuple(),
                set_supervisors=set_supervisors,
                end_of_day=end_of_day,
                prompt_responses=tuple(prompt_responses),
            ),
            "OK",
            "ok",
        )

    async def _record_input_ack_event(
        self,
        *,
        accepted: bool,
        reason_code: str,
        reason: str,
        source: str,
        tick_target: int,
        msg_type: str | None = None,
    ) -> None:
        kind = "input_accepted" if accepted else "input_rejected"
        async with self._lock:
            details: Dict[str, Any] = {
                "source": source,
                "tick_target": int(tick_target),
                "reason_code": str(reason_code),
                "reason": str(reason),
            }
            if msg_type is not None:
                details["msg_type"] = str(msg_type)
            self._kernel.record_external_event(
                kind=kind,
                details=details,
            )

    async def _broadcast_current_snapshot(self) -> None:
        state = self._kernel.state
        tick = int(state.day_tick)
        for conn in list(self._connections.values()):
            if not bool(getattr(conn.session, "_subscribed", False)):
                continue
            await self._send_snapshot(conn, state, tick=tick)
