export type ConsoleSkinTone = "neutral" | "active" | "critical";

export const CONSOLE_SKIN = {
    colors: {
        gunmetalBase: "#151b22",
        gunmetalLift: "#212b35",
        brassAccent: "#c39a52",
        stableTeal: "#5cb5ad",
        stableCyan: "#7ec7dc",
        warningAmber: "#d99a49",
        dangerCrimson: "#af4b46",
        textPrimary: "#f0ece2",
        textMuted: "#b8c0cb",
    },
    typography: {
        stripHeaderPx: 11,
        roomLabelPx: 13,
        microLabelPx: 10,
    },
    stroke: {
        bezelPx: 2,
        glassPx: 1,
    },
    radii: {
        bezelPx: 18,
        glassPx: 12,
    },
    glow: {
        none: "none",
        active: "0 0 0 1px rgba(126, 199, 220, 0.2), 0 14px 34px rgba(6, 12, 18, 0.64)",
        critical: "0 0 0 1px rgba(175, 75, 70, 0.3), 0 16px 36px rgba(24, 6, 8, 0.72)",
    },
} as const;

export type ConsoleSkin = typeof CONSOLE_SKIN;

export function borderColorForTone(tone: ConsoleSkinTone): string {
    if (tone === "active") return "rgba(126, 199, 220, 0.56)";
    if (tone === "critical") return "rgba(175, 75, 70, 0.68)";
    return "rgba(159, 170, 184, 0.46)";
}

export function glassColorForTone(tone: ConsoleSkinTone): string {
    if (tone === "active") {
        return "linear-gradient(168deg, rgba(10, 24, 32, 0.8), rgba(12, 20, 28, 0.86))";
    }
    if (tone === "critical") {
        return "linear-gradient(168deg, rgba(34, 13, 15, 0.8), rgba(18, 14, 17, 0.86))";
    }
    return "linear-gradient(168deg, rgba(15, 22, 30, 0.78), rgba(10, 16, 22, 0.84))";
}

export function glowForTone(tone: ConsoleSkinTone): string {
    if (tone === "active") return CONSOLE_SKIN.glow.active;
    if (tone === "critical") return CONSOLE_SKIN.glow.critical;
    return CONSOLE_SKIN.glow.none;
}
