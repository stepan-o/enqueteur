from __future__ import annotations

import asyncio
import copy
import json
import os
import tempfile
import unittest
import uuid
from typing import Any, Dict, List

from backend.sim_sim.config import load_sim_sim_config
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


class TestSimSimLiveEndOfDayInputContract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.sent: List[bytes] = []
        self.config_path = self._write_no_prompt_config()
        self.host = SessionHost(seed=7, config_path=self.config_path)

        async def _send_bytes(data: bytes) -> None:
            self.sent.append(data)

        self.ctx = await self.host.register_connection(send_bytes=_send_bytes)
        await self._handshake_and_subscribe()
        self.sent.clear()

    async def asyncTearDown(self) -> None:
        await self.host.unregister_connection(self.ctx)
        try:
            os.unlink(self.config_path)
        except FileNotFoundError:
            pass

    def _write_no_prompt_config(self) -> str:
        loaded = load_sim_sim_config()
        raw = copy.deepcopy(loaded.raw)
        raw["conflicts"]["hostile_pairs"] = []
        raw["guardrails"]["prevent_critical_before_day"] = 999
        raw["confidence"]["threshold_critical"] = 2.0

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            json.dump(raw, fh)
            return fh.name

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

    async def _enter_end_of_day_phase(self) -> None:
        if self.host.current_state.phase == "end_of_day":
            return
        await self._send_message(
            "SIM_INPUT",
            {
                "tick_target": 1,
            },
        )
        self.assertEqual(self.host.current_tick, 0)
        self.assertEqual(self.host.current_state.phase, "end_of_day")
        self.sent.clear()

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

    def _assert_snapshot_rebroadcast(self, *, tick: int) -> None:
        decoded = self._decoded_sent()
        self.assertTrue(
            any(
                env.get("msg_type") == "FULL_SNAPSHOT"
                and int(env.get("payload", {}).get("tick", -1)) == int(tick)
                for env in decoded
            ),
            f"expected FULL_SNAPSHOT rebroadcast at tick={tick}",
        )

    async def test_live_planning_rejects_end_of_day_payload(self) -> None:
        self.assertEqual(self.host.current_state.phase, "planning")
        await self._send_message(
            "SIM_INPUT",
            {
                "tick_target": 1,
                "end_of_day": {"upgrade_brains": 1},
            },
        )

        self.assertEqual(self.host.current_tick, 0)
        self.assertEqual(self.host.current_state.phase, "planning")
        ack = self._latest_ack_event("input_rejected")
        details = ack.get("details", {})
        self.assertEqual(details.get("reason_code"), "PLANNING_DISALLOWED_FIELDS_PRESENT")
        self.assertEqual(details.get("msg_type"), "SIM_INPUT")
        self._assert_snapshot_rebroadcast(tick=0)

    async def test_live_end_of_day_rejects_set_supervisors_payload(self) -> None:
        await self._enter_end_of_day_phase()
        self.assertEqual(self.host.current_state.phase, "end_of_day")
        await self._send_message(
            "SIM_INPUT",
            {
                "tick_target": 1,
                "set_supervisors": {"1": "S"},
            },
        )

        self.assertEqual(self.host.current_tick, 0)
        self.assertEqual(self.host.current_state.phase, "end_of_day")
        ack = self._latest_ack_event("input_rejected")
        details = ack.get("details", {})
        self.assertEqual(details.get("reason_code"), "END_OF_DAY_DISALLOWED_FIELDS_PRESENT")
        self.assertEqual(details.get("msg_type"), "SIM_INPUT")
        self._assert_snapshot_rebroadcast(tick=0)

    async def test_live_accepts_end_of_day_only_while_phase_end_of_day(self) -> None:
        await self._enter_end_of_day_phase()
        self.assertEqual(self.host.current_state.phase, "end_of_day")
        await self._send_message(
            "SIM_INPUT",
            {
                "tick_target": 1,
                "end_of_day": {"upgrade_brains": 1},
            },
        )

        self.assertEqual(self.host.current_tick, 1)
        self.assertEqual(self.host.current_state.phase, "planning")
        ack = self._latest_ack_event("input_accepted")
        details = ack.get("details", {})
        self.assertEqual(details.get("reason_code"), "INPUT_ACCEPTED")
        self.assertEqual(details.get("msg_type"), "SIM_INPUT")
