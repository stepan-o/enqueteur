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
    RIBBON_SPOOL: {
        class_code: "RIBBON_SPOOL",
        label: "Ribbon Spool",
        footprint: { w: 1, h: 1 },
        height_ref: 1.4,
        parts: [
            {
                shape: "capsule",
                size: { w: 0.8, h: 0.8, z: 1.2 },
                color: 0x89d6c8,
                emissive: 0.35,
            },
            {
                shape: "cylinder",
                size: { w: 1.0, h: 1.0, z: 0.12 },
                offset: { x: 0, y: 0, z: 1.1 },
                color: 0xd0a85a,
            },
        ],
    },
    WEAVING_MACHINE: {
        class_code: "WEAVING_MACHINE",
        label: "Weaving Machine",
        footprint: { w: 3, h: 2 },
        height_ref: 1.1,
        parts: [
            {
                shape: "box",
                size: { w: 3.0, h: 2.0, z: 0.5 },
                color: 0xc58b3c,
            },
            {
                shape: "wedge",
                size: { w: 3.0, h: 1.0, z: 0.45 },
                offset: { x: 0, y: -0.35, z: 0.5 },
                color: 0xb27d3a,
            },
            {
                shape: "panel",
                size: { w: 2.6, h: 1.0, z: 0.08 },
                offset: { x: 0, y: 0.5, z: 0.75 },
                color: 0x63d0c6,
                emissive: 0.25,
            },
        ],
    },
};

export function getObjectVisual(classCode: string): ObjectVisualSpec | undefined {
    return OBJECT_VISUALS[classCode];
}
