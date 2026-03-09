import { describe, expect, it } from "vitest";

import {
    convertLiveFrameDiff,
    convertLiveFullSnapshot,
    convertLiveKernelHello,
    convertLiveRunAnchors,
} from "../app/live/liveStateBridge";
import type { WorldState } from "../state/worldStore";

describe("Phase F4 live state bridge", () => {
    it("converts Enqueteur FULL_SNAPSHOT into world store snapshot shape", () => {
        const snapshot = convertLiveFullSnapshot({
            schema_version: "enqueteur_mbam_1",
            tick: 12,
            step_hash: "hash-12",
            state: {
                world: {
                    rooms: [{ room_id: 1, label: "Lobby", kind_code: 1, occupants: [], items: [], neighbors: [] }],
                    objects: [
                        {
                            object_id: 3002,
                            class_code: "DISPLAY_CASE",
                            room_id: 1,
                            tile_x: 0,
                            tile_y: 0,
                            size_w: 1,
                            size_h: 1,
                            orientation: 0,
                            scale: 1,
                            height: 0,
                            durability: 1,
                            efficiency: 1,
                            status_code: 0,
                            occupant_agent_id: null,
                            ticks_in_state: 0,
                        },
                    ],
                    clock: { day_index: 1, tick_in_day: 12, time_of_day: 0.5, day_phase: "evening" },
                },
                npcs: {
                    npcs: [
                        {
                            npc_id: "marc",
                            current_room_id: "security_office",
                            availability: "available",
                            trust: 0.4,
                            stress: 0.2,
                            stance: "procedural",
                            emotion: "guarded",
                            soft_alignment_hint: "order",
                            visible_behavior_flags: [],
                            current_scene_id: "S2",
                            card_state: {
                                portrait_variant: "default",
                                tell_cue: "careful",
                                suggested_interaction_mode: "be precise",
                                trust_trend: "flat",
                            },
                        },
                    ],
                },
                investigation: {
                    truth_epoch: 1,
                    objects: [],
                    evidence: {
                        discovered_ids: ["E2_CAFE_RECEIPT"],
                        collected_ids: [],
                        observed_not_collected_ids: [],
                    },
                    facts: { known_fact_ids: ["N4"] },
                    contradictions: {
                        unlockable_edge_ids: [],
                        known_edge_ids: [],
                        required_for_accusation: true,
                        requirement_satisfied: false,
                    },
                },
                dialogue: {
                    truth_epoch: 1,
                    active_scene_id: "S2",
                    scene_completion: [],
                    surfaced_scene_ids: ["S2"],
                    revealed_fact_ids: ["N4"],
                    recent_turns: [],
                    summary_rules: { required_scene_ids: ["S2"], current_scene_min_fact_count: 1 },
                    contradiction_requirement_satisfied: false,
                },
                learning: {
                    difficulty_profile: "D0",
                    active_scene_id: "S2",
                    current_hint_level: "soft_hint",
                    summary_by_scene: [],
                    minigames: [],
                    scaffolding_policy: {
                        scene_id: "S2",
                        current_hint_level: "soft_hint",
                        current_hint_rank: 0,
                        allowed_hint_levels: ["soft_hint"],
                        recommended_mode: "hint",
                        english_meta_allowed: false,
                        french_action_required: true,
                        reason_code: "default",
                        soft_hint_key: null,
                        sentence_stem_key: null,
                        rephrase_set_id: null,
                        english_meta_key: null,
                        prompt_generosity: "default",
                        confirmation_strength: "default",
                        summary_strictness: "default",
                        language_support_level: "default",
                        target_minigame_id: null,
                    },
                    recent_outcomes: [],
                },
                resolution: {
                    status: "in_progress",
                    outcome: null,
                    recap: null,
                },
            },
        });

        expect(snapshot.tick).toBe(12);
        expect(snapshot.schema_version).toBe("enqueteur_mbam_1");
        expect(snapshot.state.rooms).toHaveLength(1);
        expect(snapshot.state.objects).toHaveLength(1);
        expect(snapshot.state.npc_semantic).toHaveLength(1);
        expect(snapshot.state.dialogue?.active_scene_id).toBe("S2");
        expect(snapshot.state.dialogue?.learning?.active_scene_id).toBe("S2");
        expect(snapshot.state.investigation?.facts.known_fact_ids).toEqual(["N4"]);
    });

    it("converts Enqueteur FRAME_DIFF into world store diff ops", () => {
        const currentState = {
            mode: "live",
            tick: 12,
            stepHash: "hash-12",
            connected: true,
            desynced: false,
            world: { day_index: 1, tick_in_day: 12, time_of_day: 0.5, day_phase: "evening" },
            rooms: new Map(),
            agents: new Map(),
            items: new Map(),
            objects: new Map(),
            events: new Map(),
            caseState: null,
            npcSemantic: [],
            investigation: null,
            dialogue: null,
            caseOutcome: null,
            caseRecap: null,
        } as unknown as WorldState;

        const diff = convertLiveFrameDiff(
            {
                schema_version: "enqueteur_mbam_1",
                from_tick: 12,
                to_tick: 13,
                prev_step_hash: "hash-12",
                step_hash: "hash-13",
                ops: [
                    { op: "SET_CLOCK", clock: { day_index: 1, tick_in_day: 13, time_of_day: 0.52, day_phase: "evening" } },
                    { op: "REVEAL_EVIDENCE", evidence_id: "E2_CAFE_RECEIPT" },
                    { op: "REVEAL_FACT", fact_id: "N4" },
                    { op: "SET_ACTIVE_SCENE", scene_id: "S2" },
                    { op: "SET_HINT_LEVEL", hint_level: "sentence_stem" },
                    { op: "SET_OUTCOME", outcome: { truth_epoch: 1, primary_outcome: "in_progress", terminal: false } },
                ],
            },
            currentState
        );

        expect(diff.from_tick).toBe(12);
        expect(diff.to_tick).toBe(13);
        expect(diff.ops.some((op) => op.op === "SET_WORLD")).toBe(true);
        expect(diff.ops.some((op) => op.op === "SET_INVESTIGATION")).toBe(true);
        expect(diff.ops.some((op) => op.op === "SET_DIALOGUE")).toBe(true);
        expect(diff.ops.some((op) => op.op === "SET_CASE_OUTCOME")).toBe(true);
    });

    it("maps kernel hello anchors consistently", () => {
        const hello = {
            engine_name: "enqueteur",
            engine_version: "0.1.0",
            schema_version: "enqueteur_mbam_1",
            world_id: "world-123",
            run_id: "run-123",
            seed: "A",
            tick_rate_hz: 30,
            time_origin_ms: 0,
            render_spec: {},
        } as const;

        const kernel = convertLiveKernelHello(hello);
        const anchors = convertLiveRunAnchors(hello);
        expect(kernel.run_id).toBe("run-123");
        expect(anchors.world_id).toBe("world-123");
        expect(anchors.seed).toBe("A");
    });
});
