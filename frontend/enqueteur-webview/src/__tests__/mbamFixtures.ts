import type {
    DiffOp,
    FrameDiffPayload,
    FullSnapshotPayload,
    KvpDialogueState,
    KvpInvestigationState,
    KvpState,
    WorldState,
} from "../state/worldStore";

export function makeMbamSnapshot(tick = 1): FullSnapshotPayload {
    const state: KvpState = {
        rooms: [
            {
                room_id: 1,
                label: "MBAM Lobby",
                kind_code: 0,
                occupants: [101],
                items: [],
                neighbors: [2, 3, 5],
                tension_tier: "low",
                highlight: false,
                zone: "museum",
                level: 0,
            },
            {
                room_id: 2,
                label: "Gallery 1",
                kind_code: 1,
                occupants: [],
                items: [],
                neighbors: [1, 4],
                tension_tier: "medium",
                highlight: false,
                zone: "museum",
                level: 0,
            },
            {
                room_id: 5,
                label: "Cafe de la Rue",
                kind_code: 2,
                occupants: [],
                items: [],
                neighbors: [1],
                tension_tier: "low",
                highlight: false,
                zone: "street",
                level: 0,
            },
        ],
        agents: [
            {
                agent_id: 101,
                room_id: 1,
                role_code: 1,
                generation: 0,
                profile_traits: {},
                identity_vector: [],
                persona_style_vector: null,
                drives: {},
                emotions: {},
                key_relationships: [],
                active_motives: [],
                plan: null,
                transform: { room_id: 1, x: 1.0, y: 1.0 },
                action_state_code: 0,
                durability: 1,
                energy: 1,
                money: 0,
                smartness: 1,
                toughness: 1,
                obedience: 1,
                mission_alignment: 1,
                narrative_state_ref: null,
                cached_summary_ref: null,
            },
        ],
        items: [],
        objects: [
            {
                object_id: 3002,
                class_code: "DISPLAY_CASE",
                room_id: 1,
                tile_x: 1,
                tile_y: 1,
                size_w: 1,
                size_h: 1,
                orientation: 0,
                scale: 1,
                height: null,
                durability: 1,
                efficiency: 1,
                status_code: 0,
                occupant_agent_id: null,
                ticks_in_state: 0,
            },
            {
                object_id: 3007,
                class_code: "RECEIPT_PRINTER",
                room_id: 5,
                tile_x: 2,
                tile_y: 2,
                size_w: 1,
                size_h: 1,
                orientation: 0,
                scale: 1,
                height: null,
                durability: 1,
                efficiency: 1,
                status_code: 0,
                occupant_agent_id: null,
                ticks_in_state: 0,
            },
        ],
        world: {
            world_output: 1,
            day_index: 0,
            ticks_per_day: 1800,
            tick_in_day: tick,
            time_of_day: 18.1,
            day_phase: "evening",
            phase_progress: 0.5,
        },
        events: [],
        case: {
            case_id: "MBAM_01",
            seed: "A",
            truth_epoch: 1,
            visible_case_slice: {
                public_room_ids: ["MBAM_LOBBY", "GALLERY_AFFICHES", "CAFE_DE_LA_RUE"],
                public_object_ids: ["O1_DISPLAY_CASE", "O3_WALL_LABEL", "O4_BENCH", "O9_RECEIPT_PRINTER"],
                starting_scene_id: "S1",
                starting_known_fact_ids: ["N1"],
            },
        },
        npc_semantic: [
            {
                npc_id: "elodie",
                current_room_id: "MBAM_LOBBY",
                availability: "available",
                trust: 0,
                stress: 0,
                stance: "helpful",
                emotion: "calm",
                soft_alignment_hint: "protecting_institution",
                visible_behavior_flags: ["formal_register"],
                current_scene_id: "S1",
                card_state: {
                    portrait_variant: "calm",
                    tell_cue: "exact_times",
                    suggested_interaction_mode: "formal",
                    trust_trend: "flat",
                },
            },
            {
                npc_id: "marc",
                current_room_id: "SECURITY_OFFICE",
                availability: "restricted",
                trust: -1,
                stress: 1,
                stance: "procedural",
                emotion: "guarded",
                soft_alignment_hint: "protecting_institution",
                visible_behavior_flags: ["procedure_first"],
                current_scene_id: "S2",
                card_state: {
                    portrait_variant: "procedural",
                    tell_cue: "procedure_first",
                    suggested_interaction_mode: "procedural",
                    trust_trend: "flat",
                },
            },
        ],
        investigation: {
            truth_epoch: 1,
            objects: [
                {
                    object_id: "O1_DISPLAY_CASE",
                    affordances: ["inspect", "check_lock", "examine_surface"],
                    observed_affordances: [],
                    known_state: {},
                },
                {
                    object_id: "O9_RECEIPT_PRINTER",
                    affordances: ["ask_for_receipt", "read_receipt"],
                    observed_affordances: [],
                    known_state: {},
                },
            ],
            evidence: {
                discovered_ids: ["E2_CAFE_RECEIPT"],
                collected_ids: [],
                observed_not_collected_ids: ["clue:evidence:E2_CAFE_RECEIPT:observed_not_collected"],
            },
            facts: {
                known_fact_ids: ["N1", "N4"],
            },
            contradictions: {
                unlockable_edge_ids: ["E3"],
                known_edge_ids: [],
                required_for_accusation: true,
                requirement_satisfied: false,
            },
        },
        dialogue: {
            truth_epoch: 1,
            active_scene_id: "S1",
            scene_completion: [
                { scene_id: "S1", completion_state: "in_progress" },
                { scene_id: "S2", completion_state: "available" },
                { scene_id: "S3", completion_state: "locked" },
                { scene_id: "S4", completion_state: "locked" },
                { scene_id: "S5", completion_state: "locked" },
            ],
            surfaced_scene_ids: ["S1", "S2"],
            revealed_fact_ids: ["N1"],
            recent_turns: [
                {
                    turn_index: 0,
                    scene_id: "S1",
                    npc_id: "elodie",
                    intent_id: "ask_what_happened",
                    status: "accepted",
                    code: "ok",
                    outcome: "incident_shared",
                    response_mode: "direct",
                    revealed_fact_ids: ["N1"],
                    trust_delta: 0,
                    stress_delta: 0,
                    repair_response_mode: null,
                    summary_check_code: null,
                },
            ],
            summary_rules: {
                required_scene_ids: ["S1"],
                current_scene_min_fact_count: 1,
            },
            contradiction_requirement_satisfied: false,
        },
        debug: { source: "mbam_fixture" },
    };

    return {
        schema_version: "1",
        tick,
        state,
        step_hash: `step_${tick}`,
    };
}

export function cloneInvestigation(investigation: KvpInvestigationState): KvpInvestigationState {
    return JSON.parse(JSON.stringify(investigation)) as KvpInvestigationState;
}

export function cloneDialogue(dialogue: KvpDialogueState): KvpDialogueState {
    return JSON.parse(JSON.stringify(dialogue)) as KvpDialogueState;
}

export function makeStateDiff(
    state: WorldState,
    ops: DiffOp[],
    toTick = state.tick + 1
): FrameDiffPayload {
    return {
        schema_version: "1",
        from_tick: state.tick,
        to_tick: toTick,
        prev_step_hash: state.stepHash ?? null,
        ops,
        step_hash: `step_${toTick}`,
    };
}
