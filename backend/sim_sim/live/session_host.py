from __future__ import annotations

"""LIVE session host for sim_sim minimal vertical slice."""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Sequence

from backend.sim4.host.kvp_defaults import default_render_spec
from backend.sim4.integration.live_envelope import make_live_envelope, validate_live_envelope
from backend.sim4.integration.live_session import LiveSession
from backend.sim4.integration.manifest_schema import ALLOWED_CHANNELS
from backend.sim4.integration.render_spec import Bounds

from backend.sim_sim.kernel.state import (
    DayInput,
    SimSimKernel,
    SimSimState,
    SupervisorSwap,
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

    def __init__(self, *, seed: int) -> None:
        self._kernel = SimSimKernel(seed=seed)
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
        }
        self._render_spec = default_render_spec(
            bounds=Bounds(min_x=0.0, min_y=0.0, max_x=36.0, max_y=16.0),
            units_per_tile=1.0,
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
        envelope = ctx.codec.decode(raw_data)
        validate_live_envelope(envelope)
        msg_type = str(envelope.get("msg_type", ""))

        if msg_type == "INPUT_COMMAND":
            await self._handle_input_command(ctx, envelope)
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
            if day_input.tick_target in self._pending_inputs:
                return False, f"day input already queued for tick {day_input.tick_target}"
            self._pending_inputs[day_input.tick_target] = day_input
            logger.info("[input] accepted source=%s tick_target=%s", source, day_input.tick_target)
            return True, "accepted"

    async def advance_day(self, fallback_input: DayInput) -> tuple[int, DayInput]:
        async with self._lock:
            next_tick = self.current_tick + 1
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

    async def _handle_input_command(self, ctx: ConnectionContext, envelope: Mapping[str, Any]) -> None:
        payload = envelope.get("payload", {})
        if not isinstance(payload, dict):
            await self._send_command_rejected(
                ctx,
                client_cmd_id=str(envelope.get("msg_id", "")),
                reason="payload must be an object",
            )
            return

        client_cmd_id = str(payload.get("client_cmd_id", envelope.get("msg_id", "")))
        cmd = payload.get("cmd", {})
        if not isinstance(cmd, dict):
            await self._send_command_rejected(ctx, client_cmd_id=client_cmd_id, reason="cmd must be an object")
            return

        cmd_type = str(cmd.get("type", ""))
        tick_target = cmd.get("tick_target")
        cmd_payload = cmd.get("payload", {})
        if not isinstance(cmd_payload, dict):
            await self._send_command_rejected(
                ctx,
                client_cmd_id=client_cmd_id,
                reason="cmd.payload must be an object",
            )
            return

        if cmd_type != "SIM_SIM_DAY_INPUT":
            await self._send_command_rejected(
                ctx,
                client_cmd_id=client_cmd_id,
                reason=f"unsupported cmd.type={cmd_type}",
            )
            return

        try:
            parsed_tick_target = int(tick_target)
        except Exception:
            await self._send_command_rejected(
                ctx,
                client_cmd_id=client_cmd_id,
                reason="cmd.tick_target must be an integer",
            )
            return

        swaps: List[SupervisorSwap] = []
        for entry in cmd_payload.get("supervisor_swaps", []):
            if not isinstance(entry, dict):
                continue
            try:
                supervisor_code = resolve_supervisor_code(entry.get("supervisor_code"))
                if supervisor_code is None:
                    supervisor_code = resolve_supervisor_code(entry.get("supervisor_id"))
                if supervisor_code is None:
                    raise ValueError("unknown supervisor")
                swaps.append(
                    SupervisorSwap(
                        supervisor_code=supervisor_code,
                        room_id=int(entry.get("room_id")),
                    )
                )
            except Exception:
                await self._send_command_rejected(
                    ctx,
                    client_cmd_id=client_cmd_id,
                    reason="invalid supervisor_swaps entry",
                )
                return

        day_input = DayInput(
            tick_target=parsed_tick_target,
            advance=bool(cmd_payload.get("advance", True)),
            supervisor_swaps=tuple(swaps),
        )
        accepted, reason = await self.submit_day_input(day_input, source=f"ws:{ctx.connection_id}")
        if accepted:
            await self._send_command_accepted(
                ctx,
                client_cmd_id=client_cmd_id,
                tick_target=parsed_tick_target,
            )
        else:
            await self._send_command_rejected(
                ctx,
                client_cmd_id=client_cmd_id,
                reason=reason,
            )

    async def _send_command_accepted(self, ctx: ConnectionContext, *, client_cmd_id: str, tick_target: int) -> None:
        env = make_live_envelope(
            "COMMAND_ACCEPTED",
            {
                "client_cmd_id": client_cmd_id,
                "tick_target": int(tick_target),
            },
            msg_id=str(uuid.uuid4()),
            sent_at_ms=0,
        )
        await ctx.send_bytes(ctx.codec.encode(env))
        logger.info("[input] COMMAND_ACCEPTED id=%s tick_target=%s", client_cmd_id, tick_target)

    async def _send_command_rejected(self, ctx: ConnectionContext, *, client_cmd_id: str, reason: str) -> None:
        env = make_live_envelope(
            "COMMAND_REJECTED",
            {
                "client_cmd_id": client_cmd_id,
                "reason": str(reason),
            },
            msg_id=str(uuid.uuid4()),
            sent_at_ms=0,
        )
        await ctx.send_bytes(ctx.codec.encode(env))
        logger.info("[input] COMMAND_REJECTED id=%s reason=%s", client_cmd_id, reason)
