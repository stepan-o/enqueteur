export type Rect = {
    x: number;
    y: number;
    w: number;
    h: number;
};

export type Size = {
    w: number;
    h: number;
};

export type Padding =
    | number
    | {
          top?: number;
          right?: number;
          bottom?: number;
          left?: number;
      };

export type SafeFrame = Rect & {
    scale: number;
    viewportW: number;
    viewportH: number;
    baseW: number;
    baseH: number;
};

export type AnchorOffset = {
    x?: number;
    y?: number;
};

export type NamedRegion = {
    name: string;
    rect: Rect;
    group: "primary" | "split" | "feed" | "overlay";
};

export const CANONICAL_VIEWPORT: Size = { w: 1920, h: 1080 };

export const TOP_STRIP_RECT: Rect = { x: 24, y: 24, w: 1872, h: 104 };
export const TOP_STRIP_LEFT_CLUSTER_RECT: Rect = { x: 48, y: 42, w: 620, h: 68 };
export const TOP_STRIP_CENTER_CLUSTER_RECT: Rect = { x: 716, y: 42, w: 488, h: 68 };
export const TOP_STRIP_RIGHT_CLUSTER_RECT: Rect = { x: 1176, y: 42, w: 720, h: 68 };

export const RIGHT_COLUMN_RECT: Rect = { x: 1436, y: 152, w: 460, h: 904 };
export const RIGHT_COLUMN_DIRECTIVE_RECT: Rect = { x: 1436, y: 152, w: 460, h: 220 };
export const RIGHT_COLUMN_DOCKET_RECT: Rect = { x: 1436, y: 388, w: 460, h: 668 };

export const CCTV_WALL_RECT: Rect = { x: 24, y: 152, w: 1388, h: 684 };

export const CCTV_FEED_RECTS: Readonly<Record<number, Rect>> = {
    2: { x: 40, y: 168, w: 440, h: 317 },
    3: { x: 498, y: 168, w: 440, h: 317 },
    4: { x: 956, y: 168, w: 440, h: 317 },
    1: { x: 40, y: 503, w: 440, h: 317 },
    5: { x: 498, y: 503, w: 440, h: 317 },
    6: { x: 956, y: 503, w: 440, h: 317 },
};

export const COMMAND_DECK_RECT: Rect = { x: 24, y: 860, w: 1388, h: 196 };
export const COMMAND_DECK_LEFT_ROSTER_RECT: Rect = { x: 40, y: 876, w: 560, h: 164 };
export const COMMAND_DECK_CENTER_PRIMARY_RECT: Rect = { x: 624, y: 876, w: 420, h: 164 };
export const COMMAND_DECK_RIGHT_SECONDARY_RECT: Rect = { x: 1068, y: 876, w: 344, h: 164 };

export const OVERLAY_SPOTLIGHT_RECT: Rect = { x: 240, y: 220, w: 1440, h: 640 };
export const OVERLAY_RESOLVING_TRACKER_RECT: Rect = { x: 398, y: 176, w: 640, h: 120 };
export const OVERLAY_EOD_BAY_RECT: Rect = { x: 120, y: 260, w: 1680, h: 720 };
export const OVERLAY_RECAP_RECT: Rect = { x: 120, y: 320, w: 1680, h: 440 };

export type DirectorConsoleLayout = {
    safeFrame: SafeFrame;
    canonical: {
        topStrip: Rect;
        topStripClusters: {
            left: Rect;
            center: Rect;
            right: Rect;
        };
        rightColumn: Rect;
        rightColumnSplits: {
            directive: Rect;
            docket: Rect;
        };
        cctvWall: Rect;
        cctvFeedsByRoom: Readonly<Record<number, Rect>>;
        commandDeck: Rect;
        commandDeckZones: {
            leftRoster: Rect;
            centerPrimary: Rect;
            rightSecondary: Rect;
        };
        overlays: {
            spotlight: Rect;
            resolvingTracker: Rect;
            eodBay: Rect;
            recap: Rect;
        };
    };
    scaled: {
        topStrip: Rect;
        topStripClusters: {
            left: Rect;
            center: Rect;
            right: Rect;
        };
        rightColumn: Rect;
        rightColumnSplits: {
            directive: Rect;
            docket: Rect;
        };
        cctvWall: Rect;
        cctvFeedsByRoom: Record<number, Rect>;
        commandDeck: Rect;
        commandDeckZones: {
            leftRoster: Rect;
            centerPrimary: Rect;
            rightSecondary: Rect;
        };
        overlays: {
            spotlight: Rect;
            resolvingTracker: Rect;
            eodBay: Rect;
            recap: Rect;
        };
    };
};

export function inset(rect: Rect, padding: Padding): Rect {
    const resolved =
        typeof padding === "number"
            ? { top: padding, right: padding, bottom: padding, left: padding }
            : {
                  top: padding.top ?? 0,
                  right: padding.right ?? 0,
                  bottom: padding.bottom ?? 0,
                  left: padding.left ?? 0,
              };
    const x = rect.x + resolved.left;
    const y = rect.y + resolved.top;
    const w = Math.max(0, rect.w - resolved.left - resolved.right);
    const h = Math.max(0, rect.h - resolved.top - resolved.bottom);
    return { x, y, w, h };
}

export function anchorTopLeft(container: Rect, size: Size, offset: AnchorOffset = {}): Rect {
    return {
        x: container.x + (offset.x ?? 0),
        y: container.y + (offset.y ?? 0),
        w: size.w,
        h: size.h,
    };
}

export function anchorTopRight(container: Rect, size: Size, offset: AnchorOffset = {}): Rect {
    return {
        x: container.x + container.w - size.w - (offset.x ?? 0),
        y: container.y + (offset.y ?? 0),
        w: size.w,
        h: size.h,
    };
}

export function anchorBottomLeft(container: Rect, size: Size, offset: AnchorOffset = {}): Rect {
    return {
        x: container.x + (offset.x ?? 0),
        y: container.y + container.h - size.h - (offset.y ?? 0),
        w: size.w,
        h: size.h,
    };
}

export function anchorBottomRight(container: Rect, size: Size, offset: AnchorOffset = {}): Rect {
    return {
        x: container.x + container.w - size.w - (offset.x ?? 0),
        y: container.y + container.h - size.h - (offset.y ?? 0),
        w: size.w,
        h: size.h,
    };
}

export function scaleToFit(viewportW: number, viewportH: number, base: Size = CANONICAL_VIEWPORT): SafeFrame {
    const safeViewportW = Math.max(1, viewportW);
    const safeViewportH = Math.max(1, viewportH);
    const scale = Math.min(safeViewportW / base.w, safeViewportH / base.h);
    const w = base.w * scale;
    const h = base.h * scale;
    const x = (safeViewportW - w) * 0.5;
    const y = (safeViewportH - h) * 0.5;
    return {
        x,
        y,
        w,
        h,
        scale,
        viewportW: safeViewportW,
        viewportH: safeViewportH,
        baseW: base.w,
        baseH: base.h,
    };
}

export function mapRectToSafeFrame(rect: Rect, frame: SafeFrame): Rect {
    return {
        x: frame.x + rect.x * frame.scale,
        y: frame.y + rect.y * frame.scale,
        w: rect.w * frame.scale,
        h: rect.h * frame.scale,
    };
}

function mapFeedRects(feeds: Readonly<Record<number, Rect>>, frame: SafeFrame): Record<number, Rect> {
    const mapped: Record<number, Rect> = {};
    for (const [roomId, rect] of Object.entries(feeds)) {
        mapped[Number(roomId)] = mapRectToSafeFrame(rect, frame);
    }
    return mapped;
}

export function buildDirectorConsoleLayout(viewportW: number, viewportH: number): DirectorConsoleLayout {
    const safeFrame = scaleToFit(viewportW, viewportH);

    const canonical: DirectorConsoleLayout["canonical"] = {
        topStrip: TOP_STRIP_RECT,
        topStripClusters: {
            left: TOP_STRIP_LEFT_CLUSTER_RECT,
            center: TOP_STRIP_CENTER_CLUSTER_RECT,
            right: TOP_STRIP_RIGHT_CLUSTER_RECT,
        },
        rightColumn: RIGHT_COLUMN_RECT,
        rightColumnSplits: {
            directive: RIGHT_COLUMN_DIRECTIVE_RECT,
            docket: RIGHT_COLUMN_DOCKET_RECT,
        },
        cctvWall: CCTV_WALL_RECT,
        cctvFeedsByRoom: CCTV_FEED_RECTS,
        commandDeck: COMMAND_DECK_RECT,
        commandDeckZones: {
            leftRoster: COMMAND_DECK_LEFT_ROSTER_RECT,
            centerPrimary: COMMAND_DECK_CENTER_PRIMARY_RECT,
            rightSecondary: COMMAND_DECK_RIGHT_SECONDARY_RECT,
        },
        overlays: {
            spotlight: OVERLAY_SPOTLIGHT_RECT,
            resolvingTracker: OVERLAY_RESOLVING_TRACKER_RECT,
            eodBay: OVERLAY_EOD_BAY_RECT,
            recap: OVERLAY_RECAP_RECT,
        },
    };

    return {
        safeFrame,
        canonical,
        scaled: {
            topStrip: mapRectToSafeFrame(canonical.topStrip, safeFrame),
            topStripClusters: {
                left: mapRectToSafeFrame(canonical.topStripClusters.left, safeFrame),
                center: mapRectToSafeFrame(canonical.topStripClusters.center, safeFrame),
                right: mapRectToSafeFrame(canonical.topStripClusters.right, safeFrame),
            },
            rightColumn: mapRectToSafeFrame(canonical.rightColumn, safeFrame),
            rightColumnSplits: {
                directive: mapRectToSafeFrame(canonical.rightColumnSplits.directive, safeFrame),
                docket: mapRectToSafeFrame(canonical.rightColumnSplits.docket, safeFrame),
            },
            cctvWall: mapRectToSafeFrame(canonical.cctvWall, safeFrame),
            cctvFeedsByRoom: mapFeedRects(canonical.cctvFeedsByRoom, safeFrame),
            commandDeck: mapRectToSafeFrame(canonical.commandDeck, safeFrame),
            commandDeckZones: {
                leftRoster: mapRectToSafeFrame(canonical.commandDeckZones.leftRoster, safeFrame),
                centerPrimary: mapRectToSafeFrame(canonical.commandDeckZones.centerPrimary, safeFrame),
                rightSecondary: mapRectToSafeFrame(canonical.commandDeckZones.rightSecondary, safeFrame),
            },
            overlays: {
                spotlight: mapRectToSafeFrame(canonical.overlays.spotlight, safeFrame),
                resolvingTracker: mapRectToSafeFrame(canonical.overlays.resolvingTracker, safeFrame),
                eodBay: mapRectToSafeFrame(canonical.overlays.eodBay, safeFrame),
                recap: mapRectToSafeFrame(canonical.overlays.recap, safeFrame),
            },
        },
    };
}

export function listScaledDirectorRegions(layout: DirectorConsoleLayout): NamedRegion[] {
    const feeds = Object.entries(layout.scaled.cctvFeedsByRoom)
        .map(([roomId, rect]) => ({ name: `Feed R${roomId}`, rect, group: "feed" as const }))
        .sort((left, right) => left.name.localeCompare(right.name));

    return [
        { name: "Top Strip", rect: layout.scaled.topStrip, group: "primary" },
        { name: "Top Left Cluster", rect: layout.scaled.topStripClusters.left, group: "split" },
        { name: "Top Center Cluster", rect: layout.scaled.topStripClusters.center, group: "split" },
        { name: "Top Right Cluster", rect: layout.scaled.topStripClusters.right, group: "split" },
        { name: "Right Column", rect: layout.scaled.rightColumn, group: "primary" },
        { name: "Directive", rect: layout.scaled.rightColumnSplits.directive, group: "split" },
        { name: "Docket", rect: layout.scaled.rightColumnSplits.docket, group: "split" },
        { name: "CCTV Wall", rect: layout.scaled.cctvWall, group: "primary" },
        ...feeds,
        { name: "Command Deck", rect: layout.scaled.commandDeck, group: "primary" },
        { name: "Roster", rect: layout.scaled.commandDeckZones.leftRoster, group: "split" },
        { name: "RUN SHIFT", rect: layout.scaled.commandDeckZones.centerPrimary, group: "split" },
        { name: "Secondary", rect: layout.scaled.commandDeckZones.rightSecondary, group: "split" },
        { name: "Overlay Spotlight", rect: layout.scaled.overlays.spotlight, group: "overlay" },
        { name: "Overlay Resolving", rect: layout.scaled.overlays.resolvingTracker, group: "overlay" },
        { name: "Overlay EOD", rect: layout.scaled.overlays.eodBay, group: "overlay" },
        { name: "Overlay Recap", rect: layout.scaled.overlays.recap, group: "overlay" },
    ];
}
