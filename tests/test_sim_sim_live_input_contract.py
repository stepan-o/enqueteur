from __future__ import annotations

import asyncio
import json
import unittest
import uuid
from typing import Any, Dict, List

from backend.sim_sim.kernel.state import DayInput, PromptResponse
from backend.sim_sim.live.session_host import SessionHost


def _make_envelope(msg_type: str, payload: Dict[str, Any]) -> bytes:
    env = {
        "kvp_version": "0.1",
        "msg_type": msg_type,
        "msg_id": str(uuid.uuid4()),
        "sent_at_ms": 0,
        "payload": payload,
    }
    return json.dumps(env, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class TestSimSimLiveInputContract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.sent: List[bytes] = []
        self.host = SessionHost(seed=7)

        async def _send_bytes(data: bytes) -> None:
            self.sent.append(data)

        self.ctx = await self.host.register_connection(send_bytes=_send_bytes)
        await self._handshake_and_subscribe()
        self.sent.clear()

    async def asyncTearDown(self) -> None:
        await self.host.unregister_connection(self.ctx)

    async def _handshake_and_subscribe(self) -> None:
        await self.host.handle_client_message(
            self.ctx,
            _make_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "test-viewer",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["1", "sim_sim_1"],
                    "supports": {"diff_stream": True, "full_snapshot": True, "replay_seek": False},
                },
            ),
        )
        await self.host.handle_client_message(
            self.ctx,
            _make_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
        )
        await asyncio.sleep(0.02)

    async def _send_message(self, msg_type: str, payload: Dict[str, Any]) -> None:
        await self.host.handle_client_message(self.ctx, _make_envelope(msg_type, payload))
        await asyncio.sleep(0.02)

    async def _drive_to_awaiting_prompts(self) -> None:
        for _ in range(8):
            if self.host.current_state.phase == "awaiting_prompts":
                return
            next_tick = self.host.current_tick + 1
            day_input = DayInput(tick_target=next_tick, advance=True)
            accepted, reason = await self.host.submit_day_input(day_input, source="test")
            self.assertTrue(accepted, reason)
            await self.host.advance_day(day_input)
            await asyncio.sleep(0.02)
        self.fail("expected to reach awaiting_prompts phase")

    async def _advance_via_host(self, tick_target: int) -> int:
        day_input = DayInput(tick_target=tick_target, advance=True)
        accepted, reason = await self.host.submit_day_input(day_input, source="test-cli")
        self.assertTrue(accepted, reason)
        to_tick, _ = await self.host.advance_day(day_input)
        await asyncio.sleep(0.02)
        return int(to_tick)

    def _decoded_sent(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for item in self.sent:
            out.append(json.loads(item.decode("utf-8")))
        return out

    def _latest_stream_events(self) -> List[Dict[str, Any]]:
        decoded = self._decoded_sent()
        stream_events: List[Dict[str, Any]] = []
        for env in decoded:
            msg_type = env.get("msg_type")
            payload = env.get("payload", {})
            if not isinstance(payload, dict):
                continue
            if msg_type == "FULL_SNAPSHOT":
                state = payload.get("state", {})
                if isinstance(state, dict):
                    events = state.get("events", [])
                    if isinstance(events, list):
                        stream_events.extend([ev for ev in events if isinstance(ev, dict)])
            elif msg_type == "FRAME_DIFF":
                events = payload.get("events_append", [])
                if isinstance(events, list):
                    stream_events.extend([ev for ev in events if isinstance(ev, dict)])
        self.assertGreater(len(stream_events), 0, "expected at least one streamed event after input")
        return stream_events

    def _latest_ack_event(self, kind: str) -> Dict[str, Any]:
        events = self._latest_stream_events()
        matching = [ev for ev in events if isinstance(ev, dict) and ev.get("kind") == kind]
        self.assertGreater(len(matching), 0, f"expected at least one event kind={kind}")
        return matching[-1]

    async def test_input_command_is_rejected(self) -> None:
        await self._send_message(
            "INPUT_COMMAND",
            {
                "cmd": {
                    "type": "SIM_SIM_DAY_INPUT",
                    "tick_target": 1,
                    "payload": {"supervisor_swaps": []},
                }
            },
        )

        self.assertEqual(self.host.current_tick, 0)
        self.assertEqual(set(self.host._pending_inputs.keys()), set())  # type: ignore[attr-defined]

        ack = self._latest_ack_event("input_rejected")
        details = ack.get("details", {})
        self.assertEqual(details.get("reason_code"), "UNSUPPORTED_MSG_TYPE")
        self.assertEqual(details.get("msg_type"), "INPUT_COMMAND")

    async def test_set_workers_is_rejected_with_reason_code(self) -> None:
        await self._send_message(
            "SIM_INPUT",
            {
                "tick_target": 1,
                "set_workers": {"2": {"dumb": 1, "smart": 1}},
            },
        )

        self.assertEqual(self.host.current_tick, 0)
        self.assertEqual(set(self.host._pending_inputs.keys()), set())  # type: ignore[attr-defined]

        ack = self._latest_ack_event("input_rejected")
        details = ack.get("details", {})
        self.assertEqual(details.get("reason_code"), "DISALLOWED_FIELD_SET_WORKERS")
        self.assertEqual(details.get("msg_type"), "SIM_INPUT")

    async def test_accepts_noop_planning_input_with_wrapped_payload(self) -> None:
        await self._send_message(
            "SIM_INPUT",
            {
                "schema": "sim_sim_1",
                "tick_target": 1,
                "payload": {},
            },
        )

        self.assertEqual(self.host.current_tick, 1)
        self.assertEqual(set(self.host._pending_inputs.keys()), set())  # type: ignore[attr-defined]
        decoded = self._decoded_sent()
        self.assertTrue(
            any(env.get("msg_type") == "FRAME_DIFF" and int(env.get("payload", {}).get("to_tick", -1)) == 1 for env in decoded)
        )

    async def test_accepts_noop_planning_input_without_wrapped_payload(self) -> None:
        await self._send_message(
            "SIM_INPUT",
            {
                "tick_target": 1,
            },
        )

        self.assertEqual(self.host.current_tick, 1)
        self.assertEqual(set(self.host._pending_inputs.keys()), set())  # type: ignore[attr-defined]
        decoded = self._decoded_sent()
        self.assertTrue(
            any(env.get("msg_type") == "FRAME_DIFF" and int(env.get("payload", {}).get("to_tick", -1)) == 1 for env in decoded)
        )

    async def test_planning_rejects_prompt_responses(self) -> None:
        self.assertEqual(self.host.current_state.phase, "planning")
        await self._send_message(
            "SIM_INPUT",
            {
                "tick_target": 1,
                "prompt_responses": [{"prompt_id": "prompt_conflict_1_L_S", "choice": "support_A"}],
            },
        )

        self.assertEqual(self.host.current_tick, 0)
        self.assertEqual(set(self.host._pending_inputs.keys()), set())  # type: ignore[attr-defined]
        ack = self._latest_ack_event("input_rejected")
        details = ack.get("details", {})
        self.assertEqual(details.get("reason_code"), "DISALLOWED_FIELD_PROMPT_RESPONSES_IN_PLANNING")
        self.assertEqual(details.get("msg_type"), "SIM_INPUT")

    async def test_live_rejects_supervisor_swaps_over_budget(self) -> None:
        while self.host.current_tick < 4:
            next_tick = self.host.current_tick + 1
            day_input = DayInput(tick_target=next_tick, advance=True)
            accepted, reason = await self.host.submit_day_input(day_input, source="test-cli")
            self.assertTrue(accepted, reason)
            to_tick, _ = await self.host.advance_day(day_input)
            await asyncio.sleep(0.02)
            if to_tick < next_tick:
                unresolved = [prompt for prompt in self.host.current_state.prompts if prompt.status != "resolved"]
                self.assertTrue(unresolved)
                responses = tuple(
                    PromptResponse(prompt_id=prompt.prompt_id, choice=str(prompt.choices[0]))
                    for prompt in unresolved
                )
                resolve = DayInput(tick_target=next_tick, advance=True, prompt_responses=responses)
                accepted, reason = await self.host.submit_day_input(resolve, source="test-cli")
                self.assertTrue(accepted, reason)
                await self.host.advance_day(resolve)
                await asyncio.sleep(0.02)
        self.assertEqual(self.host.current_tick, 4)
        self.assertEqual(self.host.current_state.phase, "planning")

        await self._send_message(
            "SIM_INPUT",
            {
                "tick_target": 5,
                "set_supervisors": {"1": "S", "2": "C", "3": "W", "4": "T", "5": "L"},
            },
        )

        self.assertEqual(self.host.current_tick, 4)
        self.assertNotIn(5, self.host._pending_inputs)  # type: ignore[attr-defined]
        ack = self._latest_ack_event("input_rejected")
        details = ack.get("details", {})
        self.assertEqual(details.get("reason_code"), "SUPERVISOR_SWAP_BUDGET_EXCEEDED")
        self.assertEqual(details.get("msg_type"), "SIM_INPUT")

    async def test_live_chained_prompt_resolution_progresses_same_day(self) -> None:
        # Deterministic seed=7: by tick 4 -> tick 5 transition we hit conflict then critical prompts.
        while self.host.current_tick < 4:
            next_tick = self.host.current_tick + 1
            day_input = DayInput(tick_target=next_tick, advance=True)
            accepted, reason = await self.host.submit_day_input(day_input, source="test-cli")
            self.assertTrue(accepted, reason)
            to_tick, _ = await self.host.advance_day(day_input)
            await asyncio.sleep(0.02)
            if to_tick < next_tick:
                unresolved = [prompt for prompt in self.host.current_state.prompts if prompt.status != "resolved"]
                self.assertTrue(unresolved)
                responses = tuple(
                    PromptResponse(prompt_id=prompt.prompt_id, choice=str(prompt.choices[0]))
                    for prompt in unresolved
                )
                resolve = DayInput(tick_target=next_tick, advance=True, prompt_responses=responses)
                accepted, reason = await self.host.submit_day_input(resolve, source="test-cli")
                self.assertTrue(accepted, reason)
                await self.host.advance_day(resolve)
                await asyncio.sleep(0.02)

        self.assertEqual(self.host.current_tick, 4)
        self.assertEqual(self.host.current_state.phase, "planning")

        # First no-op input starts day 5 and should pause on conflict prompt.
        await self._send_message(
            "SIM_INPUT",
            {
                "schema": "sim_sim_1",
                "tick_target": 5,
                "payload": {},
            },
        )
        self.assertEqual(self.host.current_tick, 4)
        self.assertEqual(self.host.current_state.phase, "awaiting_prompts")
        conflict_prompt = next(
            prompt
            for prompt in self.host.current_state.prompts
            if prompt.status != "resolved" and prompt.kind == "conflict"
        )

        # Resolve conflict first; run remains awaiting due critical prompt.
        await self._send_message(
            "SIM_INPUT",
            {
                "schema": "sim_sim_1",
                "tick_target": 5,
                "payload": {
                    "prompt_responses": {
                        conflict_prompt.prompt_id: str(conflict_prompt.choices[0]),
                    }
                },
            },
        )
        self.assertEqual(self.host.current_tick, 4)
        self.assertEqual(self.host.current_state.phase, "awaiting_prompts")
        critical_prompt = next(
            prompt
            for prompt in self.host.current_state.prompts
            if prompt.status != "resolved" and prompt.kind == "critical"
        )

        # Resolve critical next; tick must advance to 5 (no conflict loop).
        await self._send_message(
            "SIM_INPUT",
            {
                "schema": "sim_sim_1",
                "tick_target": 5,
                "payload": {
                    "prompt_responses": {
                        critical_prompt.prompt_id: str(critical_prompt.choices[0]),
                    }
                },
            },
        )
        self.assertEqual(self.host.current_tick, 5)
        self.assertEqual(self.host.current_state.phase, "planning")

    async def test_live_prompt_response_unblocks_without_queue_collision(self) -> None:
        await self._drive_to_awaiting_prompts()
        self.assertEqual(self.host.current_state.phase, "awaiting_prompts")
        blocked_tick = self.host.current_tick
        tick_target = blocked_tick + 1

        # Simulate stale queue entry that must not block prompt-response resume.
        self.host._pending_inputs[tick_target] = DayInput(tick_target=tick_target, advance=True)  # type: ignore[attr-defined]

        prompt = next(prompt for prompt in self.host.current_state.prompts if prompt.status != "resolved")
        await self._send_message(
            "SIM_INPUT",
            {
                "tick_target": tick_target,
                "prompt_responses": [{"prompt_id": prompt.prompt_id, "choice": str(prompt.choices[0])}],
            },
        )

        self.assertEqual(self.host.current_tick, blocked_tick + 1)
        self.assertEqual(self.host.current_state.phase, "planning")
        self.assertFalse(self.host._pending_inputs)  # type: ignore[attr-defined]
        self.assertFalse([p for p in self.host.current_state.prompts if p.status != "resolved"])

    async def test_live_awaiting_prompts_rejects_non_prompt_fields(self) -> None:
        await self._drive_to_awaiting_prompts()
        self.assertEqual(self.host.current_state.phase, "awaiting_prompts")
        blocked_tick = self.host.current_tick
        tick_target = blocked_tick + 1

        await self._send_message(
            "SIM_INPUT",
            {
                "tick_target": tick_target,
                "set_supervisors": {"2": "S"},
                "prompt_responses": [],
            },
        )

        self.assertEqual(self.host.current_tick, blocked_tick)
        self.assertEqual(self.host.current_state.phase, "awaiting_prompts")
        ack = self._latest_ack_event("input_rejected")
        details = ack.get("details", {})
        self.assertEqual(details.get("reason_code"), "AWAITING_PROMPTS_DISALLOWED_FIELDS_PRESENT")
        self.assertEqual(details.get("msg_type"), "SIM_INPUT")

    async def test_live_awaiting_prompts_requires_prompt_responses(self) -> None:
        await self._drive_to_awaiting_prompts()
        self.assertEqual(self.host.current_state.phase, "awaiting_prompts")
        blocked_tick = self.host.current_tick
        tick_target = blocked_tick + 1

        await self._send_message(
            "SIM_INPUT",
            {
                "tick_target": tick_target,
            },
        )

        self.assertEqual(self.host.current_tick, blocked_tick)
        self.assertEqual(self.host.current_state.phase, "awaiting_prompts")
        rejected = self._latest_ack_event("input_rejected")
        self.assertEqual(
            rejected.get("details", {}).get("reason_code"),
            "AWAITING_PROMPTS_PROMPT_RESPONSES_REQUIRED",
        )

    async def test_live_allows_multiple_prompt_response_updates_same_tick_target(self) -> None:
        await self._drive_to_awaiting_prompts()
        self.assertEqual(self.host.current_state.phase, "awaiting_prompts")
        blocked_tick = self.host.current_tick
        tick_target = blocked_tick + 1
        prompt = next(prompt for prompt in self.host.current_state.prompts if prompt.status != "resolved")

        # First attempt: invalid choice (rejected, tick unchanged).
        await self._send_message(
            "SIM_INPUT",
            {
                "tick_target": tick_target,
                "prompt_responses": [{"prompt_id": prompt.prompt_id, "choice": "__invalid_choice__"}],
            },
        )
        self.assertEqual(self.host.current_tick, blocked_tick)
        self.assertEqual(self.host.current_state.phase, "awaiting_prompts")
        rejected = self._latest_ack_event("input_rejected")
        self.assertEqual(rejected.get("details", {}).get("reason_code"), "PROMPT_CHOICE_INVALID")

        # Second attempt: valid choice should advance, without queue-collision rejection.
        await self._send_message(
            "SIM_INPUT",
            {
                "tick_target": tick_target,
                "prompt_responses": [{"prompt_id": prompt.prompt_id, "choice": str(prompt.choices[0])}],
            },
        )
        self.assertEqual(self.host.current_tick, blocked_tick + 1)
        self.assertEqual(self.host.current_state.phase, "planning")
        self.assertFalse(self.host._pending_inputs)  # type: ignore[attr-defined]

    async def test_live_rejects_unknown_prompt_id_with_specific_code(self) -> None:
        await self._drive_to_awaiting_prompts()
        self.assertEqual(self.host.current_state.phase, "awaiting_prompts")
        blocked_tick = self.host.current_tick
        tick_target = blocked_tick + 1

        await self._send_message(
            "SIM_INPUT",
            {
                "tick_target": tick_target,
                "prompt_responses": [{"prompt_id": "prompt_does_not_exist", "choice": "support_A"}],
            },
        )

        self.assertEqual(self.host.current_tick, blocked_tick)
        self.assertEqual(self.host.current_state.phase, "awaiting_prompts")
        rejected = self._latest_ack_event("input_rejected")
        self.assertEqual(rejected.get("details", {}).get("reason_code"), "PROMPT_ID_UNKNOWN")

    async def test_live_accepts_wrapped_prompt_response_payload_shape(self) -> None:
        await self._drive_to_awaiting_prompts()
        self.assertEqual(self.host.current_state.phase, "awaiting_prompts")
        blocked_tick = self.host.current_tick
        tick_target = blocked_tick + 1
        prompt = next(prompt for prompt in self.host.current_state.prompts if prompt.status != "resolved")

        await self._send_message(
            "SIM_INPUT",
            {
                "schema": "sim_sim_1",
                "tick_target": tick_target,
                "payload": {
                    "prompt_responses": {
                        prompt.prompt_id: str(prompt.choices[0]),
                    }
                },
            },
        )

        self.assertEqual(self.host.current_tick, blocked_tick + 1)
        self.assertEqual(self.host.current_state.phase, "planning")
        decoded = self._decoded_sent()
        self.assertTrue(any(env.get("msg_type") in ("FRAME_DIFF", "FULL_SNAPSHOT") for env in decoded))

    async def test_live_prompt_resolution_over_live_regression(self) -> None:
        # Connected fake WS client starts from tick 0 after setup.
        self.assertEqual(self.host.current_tick, 0)
        self.assertEqual(self.host.current_state.phase, "planning")

        # Advance to tick 1 via host/CLI style path.
        to_tick = await self._advance_via_host(1)
        self.assertEqual(to_tick, 1)
        self.assertEqual(self.host.current_tick, 1)
        self.assertEqual(self.host.current_state.phase, "planning")

        # Attempt to advance to tick 2; deterministic seed=7 should enter awaiting_prompts first.
        to_tick = await self._advance_via_host(2)
        self.assertEqual(to_tick, 1)
        self.assertEqual(self.host.current_tick, 1)
        self.assertEqual(self.host.current_state.phase, "awaiting_prompts")
        unresolved = [prompt for prompt in self.host.current_state.prompts if prompt.status != "resolved"]
        self.assertGreater(len(unresolved), 0)

        decoded_before = self._decoded_sent()
        awaiting_snapshots = [
            env
            for env in decoded_before
            if env.get("msg_type") == "FULL_SNAPSHOT"
            and int(env.get("payload", {}).get("tick", -1)) == 1
        ]
        self.assertGreater(len(awaiting_snapshots), 0, "expected FULL_SNAPSHOT while awaiting prompts")

        prompt = unresolved[0]
        before_count = len(decoded_before)

        # Resolve via LIVE SIM_INPUT prompt response.
        await self._send_message(
            "SIM_INPUT",
            {
                "schema": "sim_sim_1",
                "tick_target": 2,
                "payload": {
                    "prompt_responses": {
                        prompt.prompt_id: str(prompt.choices[0]),
                    }
                },
            },
        )

        decoded_after = self._decoded_sent()
        self.assertGreater(len(decoded_after), before_count, "expected subsequent publish after prompt response")
        self.assertEqual(self.host.current_tick, 2)
        self.assertEqual(self.host.current_state.phase, "planning")
        self.assertFalse([p for p in self.host.current_state.prompts if p.status != "resolved"])
        self.assertTrue(
            any(
                env.get("msg_type") == "FRAME_DIFF"
                and int(env.get("payload", {}).get("to_tick", -1)) == 2
                for env in decoded_after
            ),
            "expected FRAME_DIFF advancing to tick 2",
        )

        # Regression assertion: prompt response must not be rejected due to queue collisions.
        all_events: List[Dict[str, Any]] = []
        for env in decoded_after:
            if env.get("msg_type") == "FULL_SNAPSHOT":
                events = env.get("payload", {}).get("state", {}).get("events", [])
                if isinstance(events, list):
                    all_events.extend([ev for ev in events if isinstance(ev, dict)])
            elif env.get("msg_type") == "FRAME_DIFF":
                events = env.get("payload", {}).get("events_append", [])
                if isinstance(events, list):
                    all_events.extend([ev for ev in events if isinstance(ev, dict)])

        queued_rejections = [
            ev
            for ev in all_events
            if ev.get("kind") == "input_rejected"
            and isinstance(ev.get("details"), dict)
            and "already queued" in str(ev.get("details", {}).get("reason", ""))
        ]
        self.assertEqual(len(queued_rejections), 0, "prompt response should not hit already-queued rejection")
