// src/render/iso.ts

/**
 * Isometric projection helper (WEBVIEW-0001)
 * ------------------------------------------
 * Converts world-space coordinates into
 * screen-space isometric coordinates.
 *
 * IMPORTANT:
 * - Viewer-only
 * - No kernel assumptions
 * - Replaceable per viewer
 */

export type Vec2 = { x: number; y: number };

// Standard 2:1 isometric projection
const ISO_TILE_WIDTH = 64;
const ISO_TILE_HEIGHT = 32;

export function isoProject(p: Vec2): Vec2 {
    return {
        x: (p.x - p.y) * (ISO_TILE_WIDTH / 2),
        y: (p.x + p.y) * (ISO_TILE_HEIGHT / 2),
    };
}
