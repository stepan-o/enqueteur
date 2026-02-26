from __future__ import annotations

import asyncio
import json
import unittest
import uuid
from typing import Any, Dict, List

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

    def _decoded_sent(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for item in self.sent:
            out.append(json.loads(item.decode("utf-8")))
        return out

    def _latest_snapshot_events(self) -> List[Dict[str, Any]]:
        decoded = self._decoded_sent()
        snapshots = [env for env in decoded if env.get("msg_type") == "FULL_SNAPSHOT"]
        self.assertGreater(len(snapshots), 0, "expected at least one FULL_SNAPSHOT after input ack")
        payload = snapshots[-1].get("payload", {})
        state = payload.get("state", {})
        events = state.get("events", [])
        self.assertIsInstance(events, list)
        return events

    def _latest_ack_event(self, kind: str) -> Dict[str, Any]:
        events = self._latest_snapshot_events()
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

    async def test_malformed_sim_input_is_rejected_with_reason_code(self) -> None:
        await self._send_message(
            "SIM_INPUT",
            {
                "tick_target": 2,
                "set_workers": {"2": {"dumb": 1, "smart": 1}},
                "end_of_day": {
                    "sell_washed_dumb": 0,
                    "sell_washed_smart": 0,
                    "convert_workers_dumb": 0,
                    "convert_workers_smart": 0,
                    "upgrade_brains": 0,
                },
                "prompt_responses": [],
            },
        )

        self.assertEqual(self.host.current_tick, 0)
        self.assertEqual(set(self.host._pending_inputs.keys()), set())  # type: ignore[attr-defined]

        ack = self._latest_ack_event("input_rejected")
        details = ack.get("details", {})
        self.assertEqual(details.get("reason_code"), "INVALID_TICK_TARGET")
        self.assertEqual(details.get("msg_type"), "SIM_INPUT")

    async def test_valid_sim_input_is_accepted(self) -> None:
        await self._send_message(
            "SIM_INPUT",
            {
                "tick_target": 1,
                "set_supervisors": {"2": "S"},
                "set_workers": {"2": {"dumb": 2, "smart": 1}},
                "end_of_day": {
                    "sell_washed_dumb": 0,
                    "sell_washed_smart": 0,
                    "convert_workers_dumb": 0,
                    "convert_workers_smart": 0,
                    "upgrade_brains": 0,
                },
                "prompt_responses": [],
            },
        )

        self.assertEqual(self.host.current_tick, 0)
        self.assertIn(1, self.host._pending_inputs)  # type: ignore[attr-defined]

        ack = self._latest_ack_event("input_accepted")
        details = ack.get("details", {})
        self.assertEqual(details.get("reason_code"), "INPUT_ACCEPTED")
        self.assertEqual(details.get("tick_target"), 1)
        self.assertEqual(details.get("msg_type"), "SIM_INPUT")
