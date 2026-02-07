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

// Standard 2:1 isometric projection (mutable for renderSpec overrides)
let isoTileWidth = 64;
let isoTileHeight = 32;

export function setIsoTileSize(width: number, height: number): void {
    if (Number.isFinite(width) && Number.isFinite(height) && width > 0 && height > 0) {
        isoTileWidth = width;
        isoTileHeight = height;
    }
}

export function isoProject(p: Vec2): Vec2 {
    return {
        x: (p.x - p.y) * (isoTileWidth / 2),
        y: (p.x + p.y) * (isoTileHeight / 2),
    };
}
