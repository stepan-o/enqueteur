export type RoomArtKey =
    | "security"
    | "neural_lattice_forge"
    | "burnin_theatre"
    | "cognition_substrate_brewery"
    | "synapse_weaving_gallery"
    | "cortex_assembly_line";

const ROOM_ART_BY_ID: Record<number, RoomArtKey> = {
    1: "security",
    2: "neural_lattice_forge",
    3: "burnin_theatre",
    4: "cognition_substrate_brewery",
    5: "synapse_weaving_gallery",
    6: "cortex_assembly_line",
};

export function roomArtKeyForRoomId(roomId: number): RoomArtKey {
    return ROOM_ART_BY_ID[roomId] ?? "cortex_assembly_line";
}
