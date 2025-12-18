// src/debug/mockKernel.ts
import type { WorldStore } from "../state/worldStore";
import type { FullSnapshot } from "../state/worldStore";

/**
 * DEV-ONLY: Inject a fake FULL_SNAPSHOT into the WorldStore
 * so we can validate the viewer render pipeline without a kernel.
 */
export function injectMockSnapshot(store: WorldStore): void {
    const snap: FullSnapshot = {
        schema_version: "2",
        tick: 1,
        step_hash: "dev_mock_step_hash_0001",

        world: {
            rooms: [
                {
                    room_id: 1,
                    name: "plaza",
                    bounds: { x: 0, y: 0, w: 8, h: 6 },
                    occupancy: 2,
                    tension: 12,
                },
                {
                    room_id: 2,
                    name: "alley",
                    bounds: { x: 9, y: 1, w: 5, h: 4 },
                    occupancy: 1,
                    tension: 35,
                },
                {
                    room_id: 3,
                    name: "cafe",
                    bounds: { x: 3, y: 7, w: 6, h: 5 },
                    occupancy: 3,
                    tension: 5,
                },
            ],
        },

        agents: [
            {
                agent_id: 101,
                room_id: 1,
                pos: { x: 2, y: 2 },
                public_state: { label: "Architect-00", speaking: true },
            },
            {
                agent_id: 102,
                room_id: 1,
                pos: { x: 5, y: 3 },
                public_state: { label: "Courier", speaking: false },
            },
            {
                agent_id: 103,
                room_id: 2,
                pos: { x: 11, y: 3 },
                public_state: { label: "Rumor-Monk", speaking: false },
            },
        ],

        narrative_fragments: [
            {
                entity_id: 101,
                kind: "INNER_MONOLOGUE",
                text: "i can feel the city trying to become a story",
                ttl_ticks: 120,
                nondeterministic: true,
            },
            {
                entity_id: 103,
                kind: "DIALOGUE",
                text: "something happened last night. nobody wants to say it first.",
                ttl_ticks: 90,
                nondeterministic: true,
            },
        ],
    };

    store.applySnapshot(snap);
}
