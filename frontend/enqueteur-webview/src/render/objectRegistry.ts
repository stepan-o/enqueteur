// src/render/objectRegistry.ts

export type ObjectPartShape = "box" | "panel" | "capsule" | "cylinder" | "wedge";

export type ObjectPartSpec = {
    shape: ObjectPartShape;
    size: { w: number; h: number; z: number };
    offset?: { x: number; y: number; z: number };
    color?: number;
    emissive?: number;
    opacity?: number;
};

export type ObjectVisualSpec = {
    class_code: string;
    label: string;
    footprint: { w: number; h: number };
    height_ref?: number;
    parts: ObjectPartSpec[];
};

export const OBJECT_VISUALS: Record<string, ObjectVisualSpec> = {
    DISPLAY_CASE: {
        class_code: "DISPLAY_CASE",
        label: "Display Case",
        footprint: { w: 3, h: 2 },
        height_ref: 1.4,
        parts: [
            { shape: "box", size: { w: 3.0, h: 2.0, z: 0.8 }, color: 0xc8c1b2 },
            { shape: "panel", size: { w: 2.8, h: 1.8, z: 0.06 }, offset: { x: 0, y: 0, z: 0.88 }, color: 0x7fd0df, emissive: 0.2 },
        ],
    },
    SECURITY_TERMINAL: {
        class_code: "SECURITY_TERMINAL",
        label: "Security Terminal",
        footprint: { w: 2, h: 1 },
        height_ref: 1.2,
        parts: [
            { shape: "box", size: { w: 1.8, h: 0.9, z: 1.0 }, color: 0x4a5564 },
            { shape: "panel", size: { w: 1.5, h: 0.5, z: 0.08 }, offset: { x: 0, y: 0, z: 0.82 }, color: 0x80e3b8, emissive: 0.35 },
        ],
    },
    LOBBY_DESK: {
        class_code: "LOBBY_DESK",
        label: "Lobby Desk",
        footprint: { w: 2, h: 1 },
        height_ref: 1.0,
        parts: [
            { shape: "box", size: { w: 2.0, h: 1.0, z: 0.7 }, color: 0xa77f5a },
            { shape: "panel", size: { w: 1.8, h: 0.8, z: 0.06 }, offset: { x: 0, y: 0, z: 0.72 }, color: 0xd8c6ae },
        ],
    },
    DELIVERY_CART: {
        class_code: "DELIVERY_CART",
        label: "Delivery Cart",
        footprint: { w: 2, h: 1 },
        height_ref: 1.0,
        parts: [
            { shape: "box", size: { w: 1.8, h: 0.9, z: 0.45 }, color: 0x8893a1 },
            { shape: "capsule", size: { w: 0.3, h: 0.3, z: 0.3 }, offset: { x: -0.6, y: -0.25, z: 0.1 }, color: 0x33404d },
            { shape: "capsule", size: { w: 0.3, h: 0.3, z: 0.3 }, offset: { x: 0.6, y: 0.25, z: 0.1 }, color: 0x33404d },
        ],
    },
    CAFE_COUNTER: {
        class_code: "CAFE_COUNTER",
        label: "Cafe Counter",
        footprint: { w: 3, h: 1 },
        height_ref: 1.2,
        parts: [
            { shape: "box", size: { w: 3.0, h: 1.0, z: 0.9 }, color: 0x996d4f },
            { shape: "panel", size: { w: 2.8, h: 0.8, z: 0.06 }, offset: { x: 0, y: 0, z: 0.92 }, color: 0xd6b89c },
        ],
    },
    RECEIPT_PRINTER: {
        class_code: "RECEIPT_PRINTER",
        label: "Receipt Printer",
        footprint: { w: 1, h: 1 },
        height_ref: 0.9,
        parts: [
            { shape: "box", size: { w: 0.9, h: 0.7, z: 0.55 }, color: 0x515a67 },
            { shape: "panel", size: { w: 0.5, h: 0.2, z: 0.03 }, offset: { x: 0, y: 0, z: 0.58 }, color: 0xe8f1f4 },
        ],
    },
    BULLETIN_BOARD: {
        class_code: "BULLETIN_BOARD",
        label: "Bulletin Board",
        footprint: { w: 1, h: 1 },
        height_ref: 1.6,
        parts: [
            { shape: "panel", size: { w: 1.0, h: 0.2, z: 1.4 }, color: 0x6f7a83 },
            { shape: "panel", size: { w: 0.8, h: 0.1, z: 1.0 }, offset: { x: 0, y: 0, z: 1.2 }, color: 0xf2d58d, emissive: 0.1 },
        ],
    },
    BENCH: {
        class_code: "BENCH",
        label: "Bench",
        footprint: { w: 2, h: 1 },
        height_ref: 0.7,
        parts: [
            { shape: "box", size: { w: 1.8, h: 0.6, z: 0.25 }, color: 0x745b45 },
            { shape: "box", size: { w: 1.6, h: 0.3, z: 0.12 }, offset: { x: 0, y: 0, z: 0.35 }, color: 0x9b7b5f },
        ],
    },
};

export function getObjectVisual(classCode: string): ObjectVisualSpec | undefined {
    return OBJECT_VISUALS[classCode];
}
