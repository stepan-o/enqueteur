// src/ui/timeLighting.ts
import type { WorldMeta } from "../state/worldStore";

export type TimeLightingHandle = {
    update: (world: WorldMeta | null) => void;
};

export function mountTimeLighting(mountEl: HTMLElement): TimeLightingHandle {
    const overlay = document.createElement("div");
    overlay.className = "time-lighting";
    mountEl.appendChild(overlay);

    const update = (world: WorldMeta | null): void => {
        const t = world?.time_of_day;
        if (t === undefined || !Number.isFinite(t)) {
            overlay.style.opacity = "0";
            mountEl.style.background = "";
            return;
        }

        const phase = (world?.day_phase ?? "day").toLowerCase();
        const progress = Number.isFinite(world?.phase_progress) ? clamp(world?.phase_progress as number, 0, 1) : 0;

        const { sky, tint, alpha } = lightingFromPhase(phase, progress);
        overlay.style.backgroundColor = tint;
        overlay.style.opacity = String(alpha);
        mountEl.style.background = `radial-gradient(80% 120% at 30% 20%, ${sky} 0%, #0b1118 75%)`;
    };

    return { update };
}

function lightingFromPhase(
    phase: string,
    progress: number
): { sky: string; tint: string; alpha: number } {
    const p = clamp(progress, 0, 1);
    const NIGHT = "#0b1118";
    const DAWN = "#2a3a45";
    const DAY = "#eef5f7";
    const DUSK = "#3a2a35";

    const NIGHT_T = "#0b1015";
    const DAWN_T = "#3a2a1f";
    const DAY_T = "#ffffff";
    const DUSK_T = "#2c1f2a";

    const NIGHT_A = 0.32;
    const DAWN_A = 0.18;
    const DAY_A = 0.0;
    const DUSK_A = 0.22;

    if (phase === "dawn") {
        if (p < 0.5) {
            return {
                sky: lerpHex(NIGHT, DAWN, p * 2),
                tint: lerpHex(NIGHT_T, DAWN_T, p * 2),
                alpha: lerp(NIGHT_A, DAWN_A, p * 2),
            };
        }
        return {
            sky: lerpHex(DAWN, DAY, (p - 0.5) * 2),
            tint: lerpHex(DAWN_T, DAY_T, (p - 0.5) * 2),
            alpha: lerp(DAWN_A, DAY_A, (p - 0.5) * 2),
        };
    }
    if (phase === "dusk") {
        if (p < 0.5) {
            return {
                sky: lerpHex(DAY, DUSK, p * 2),
                tint: lerpHex(DAY_T, DUSK_T, p * 2),
                alpha: lerp(DAY_A, DUSK_A, p * 2),
            };
        }
        return {
            sky: lerpHex(DUSK, NIGHT, (p - 0.5) * 2),
            tint: lerpHex(DUSK_T, NIGHT_T, (p - 0.5) * 2),
            alpha: lerp(DUSK_A, NIGHT_A, (p - 0.5) * 2),
        };
    }
    if (phase === "night") {
        return { sky: NIGHT, tint: NIGHT_T, alpha: NIGHT_A };
    }
    return { sky: DAY, tint: DAY_T, alpha: DAY_A };
}

function clamp(v: number, min: number, max: number): number {
    return Math.min(max, Math.max(min, v));
}

function lerp(a: number, b: number, t: number): number {
    return a + (b - a) * t;
}

function lerpHex(a: string, b: string, t: number): string {
    const av = hexToRgb(a);
    const bv = hexToRgb(b);
    const clamped = clamp(t, 0, 1);
    const r = Math.round(lerp(av.r, bv.r, clamped));
    const g = Math.round(lerp(av.g, bv.g, clamped));
    const bch = Math.round(lerp(av.b, bv.b, clamped));
    return `rgb(${r}, ${g}, ${bch})`;
}

function hexToRgb(hex: string): { r: number; g: number; b: number } {
    const cleaned = hex.replace("#", "");
    const num = parseInt(cleaned, 16);
    return {
        r: (num >> 16) & 0xff,
        g: (num >> 8) & 0xff,
        b: num & 0xff,
    };
}
