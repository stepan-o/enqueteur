export type UiSfxKey = "hover" | "select" | "dismiss";

export type UiAudio = {
    setEnabled(enabled: boolean): void;
    setVolume(volume01: number): void;
    load(map: Partial<Record<UiSfxKey, string>>): Promise<void>;
    play(key: UiSfxKey): void;
};

export const DEFAULT_UI_SFX_URLS: Record<UiSfxKey, string> = {
    hover: "/assets/ui/sfx/hover_1.wav",
    select: "/assets/ui/sfx/select_1.wav",
    dismiss: "/assets/ui/sfx/dismiss_1.wav",
};

const SFX_COOLDOWN_MS: Record<UiSfxKey, number> = {
    hover: 85,
    dismiss: 100,
    select: 150,
};

const DEV = typeof import.meta !== "undefined" && Boolean(import.meta.env?.DEV);

export function createUiAudio(): UiAudio {
    let enabled = true;
    let volume = 0.35;
    let fallbackCtx: AudioContext | null = null;
    const audioByKey = new Map<UiSfxKey, HTMLAudioElement>();
    const urlByKey = new Map<UiSfxKey, string>();
    const lastPlayedAt = new Map<UiSfxKey, number>();
    const warned = new Set<string>();

    const logDevOnce = (id: string, message: string, error?: unknown): void => {
        if (!DEV || warned.has(id)) return;
        warned.add(id);
        if (error !== undefined) {
            console.warn(message, error);
            return;
        }
        console.warn(message);
    };

    const applyVolume = (): void => {
        for (const audio of audioByKey.values()) {
            audio.volume = volume;
        }
    };

    return {
        setEnabled(nextEnabled: boolean): void {
            enabled = nextEnabled;
        },
        setVolume(nextVolume01: number): void {
            const clamped = Number.isFinite(nextVolume01) ? Math.max(0, Math.min(1, Number(nextVolume01))) : 0.35;
            volume = clamped;
            applyVolume();
        },
        async load(map: Partial<Record<UiSfxKey, string>>): Promise<void> {
            const entries = Object.entries(map) as Array<[UiSfxKey, string]>;
            for (const [key, url] of entries) {
                if (!url || !url.trim()) continue;
                urlByKey.set(key, url);
                const audio = ensureAudioForKey(key, url, { eagerLoad: true, onError: (error) => {
                    logDevOnce(`load:${key}:${url}`, `[sim_sim][ui-audio] failed to load '${key}' from ${url}; SFX disabled for this key.`, error);
                } });
                audio.volume = volume;
            }
        },
        play(key: UiSfxKey): void {
            if (!enabled) return;
            const url = urlByKey.get(key);
            const audio = audioByKey.get(key) ?? (url ? ensureAudioForKey(key, url, {
                eagerLoad: false,
                onError: (error) => {
                    logDevOnce(`play-load:${key}:${url}`, `[sim_sim][ui-audio] could not initialize '${key}' from ${url}; continuing silently.`, error);
                },
            }) : undefined);
            const now = Date.now();
            const cooldownMs = SFX_COOLDOWN_MS[key] ?? 120;
            const last = lastPlayedAt.get(key) ?? 0;
            if ((now - last) < cooldownMs) return;
            lastPlayedAt.set(key, now);
            if (!audio) {
                playFallbackTone(key);
                return;
            }
            try {
                audio.currentTime = 0;
            } catch {
                // ignore seek reset issues
            }
            void audio.play().catch((error) => {
                logDevOnce(`play:${key}`, `[sim_sim][ui-audio] playback unavailable for '${key}' (continuing silently).`, error);
                playFallbackTone(key);
            });
        },
    };

    function ensureAudioForKey(
        key: UiSfxKey,
        url: string,
        opts: {
            eagerLoad: boolean;
            onError: (error: unknown) => void;
        }
    ): HTMLAudioElement {
        const existing = audioByKey.get(key);
        if (existing) return existing;
        const audio = new Audio();
        audio.preload = "auto";
        audio.src = url;
        audio.volume = volume;
        audio.addEventListener("error", (event) => {
            opts.onError(event);
        });
        if (opts.eagerLoad) {
            try {
                audio.load();
            } catch (error) {
                opts.onError(error);
            }
        }
        audioByKey.set(key, audio);
        return audio;
    }

    function ensureFallbackAudioContext(): AudioContext | null {
        if (typeof globalThis === "undefined") return null;
        if (fallbackCtx) return fallbackCtx;
        const audioGlobal = globalThis as unknown as {
            AudioContext?: new () => AudioContext;
            webkitAudioContext?: new () => AudioContext;
        };
        const Ctor = audioGlobal.AudioContext ?? audioGlobal.webkitAudioContext;
        if (!Ctor) return null;
        try {
            fallbackCtx = new Ctor();
        } catch {
            fallbackCtx = null;
        }
        return fallbackCtx;
    }

    function playFallbackTone(key: UiSfxKey): void {
        const ctx = ensureFallbackAudioContext();
        if (!ctx) return;
        if (ctx.state === "suspended") {
            void ctx.resume().catch(() => undefined);
        }
        const startAt = ctx.currentTime + 0.002;
        const amp = ctx.createGain();
        const osc = ctx.createOscillator();
        const profile = fallbackToneProfile(key, volume);

        osc.type = profile.type;
        osc.frequency.setValueAtTime(profile.fromHz, startAt);
        osc.frequency.exponentialRampToValueAtTime(profile.toHz, startAt + profile.durationSec);
        amp.gain.setValueAtTime(0.0001, startAt);
        amp.gain.exponentialRampToValueAtTime(profile.gain, startAt + 0.015);
        amp.gain.exponentialRampToValueAtTime(0.0001, startAt + profile.durationSec);

        osc.connect(amp);
        amp.connect(ctx.destination);
        osc.start(startAt);
        osc.stop(startAt + profile.durationSec + 0.03);
    }
}

function fallbackToneProfile(
    key: UiSfxKey,
    volume: number
): { type: "sine" | "square" | "sawtooth" | "triangle"; fromHz: number; toHz: number; durationSec: number; gain: number } {
    const gain = Math.max(0.005, Math.min(0.08, 0.028 * Math.max(0, Math.min(1, volume)) + 0.006));
    if (key === "hover") return { type: "triangle", fromHz: 520, toHz: 690, durationSec: 0.08, gain };
    if (key === "dismiss") return { type: "triangle", fromHz: 430, toHz: 290, durationSec: 0.1, gain };
    return { type: "square", fromHz: 640, toHz: 920, durationSec: 0.11, gain: gain * 1.1 };
}
