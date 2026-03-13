import { describe, expect, it } from "vitest";

import type { KvpRoom } from "../state/worldStore";
import { __testOnly } from "../render/pixiScene";

function makeRoom(overrides: Partial<KvpRoom>): KvpRoom {
    return {
        room_id: 1,
        label: "Salle",
        kind_code: 0,
        occupants: [],
        items: [],
        neighbors: [],
        tension_tier: "low",
        highlight: false,
        bounds: { min_x: 0, min_y: 0, max_x: 8, max_y: 8 },
        zone: "museum",
        level: 0,
        ...overrides,
    };
}

describe("P1A pixi room layout semantics", () => {
    it("derives room roles from stable metadata instead of localized labels", () => {
        const lobby = makeRoom({
            room_id: 10,
            label: "Hall MBAM",
            kind_code: 1,
            zone: "public",
            highlight: true,
            neighbors: [11, 12, 13],
            bounds: { min_x: 0, min_y: 0, max_x: 9, max_y: 8 },
        });
        const connector = makeRoom({
            room_id: 11,
            label: "Couloir de service",
            kind_code: 4,
            zone: "restricted",
            neighbors: [10],
            bounds: { min_x: 9, min_y: 2, max_x: 16, max_y: 7 },
        });
        const gallery = makeRoom({
            room_id: 12,
            label: "Salle des affiches",
            kind_code: 2,
            zone: "exhibit",
            highlight: true,
            neighbors: [10, 11],
            bounds: { min_x: 10, min_y: 0, max_x: 20, max_y: 9 },
        });
        const cafe = makeRoom({
            room_id: 13,
            label: "Cafe de la Rue",
            kind_code: 5,
            zone: "street",
            neighbors: [10],
            bounds: { min_x: 0, min_y: 8, max_x: 12, max_y: 14 },
        });
        const office = makeRoom({
            room_id: 14,
            label: "Bureau du superviseur",
            kind_code: 3,
            zone: "control",
            level: 1,
            neighbors: [11],
            bounds: { min_x: 4, min_y: 14, max_x: 10, max_y: 20 },
        });

        expect(__testOnly.pickLobbyRoom([gallery, connector, cafe, lobby])?.room_id).toBe(lobby.room_id);
        expect(__testOnly.pickConnectorRoom([gallery, connector, cafe, lobby], lobby)?.room_id).toBe(connector.room_id);
        expect(__testOnly.isOutdoorRoom(cafe)).toBe(true);
        expect(__testOnly.isUpperFloorRoom(office)).toBe(true);
        expect(__testOnly.isConnectorRoom(connector)).toBe(true);
        expect(__testOnly.roomTileSize(lobby)).toEqual([1, 2]);
        expect(__testOnly.roomTileSize(connector)).toEqual([2, 1]);
        expect(__testOnly.roomTileSize(gallery)).toEqual([2, 2]);
    });
});
