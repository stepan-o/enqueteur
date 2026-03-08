export type MbamSeedId = "A" | "B" | "C";

type MbamSeedEnv = Partial<Record<`VITE_WEBVIEW_RUN_BASE_MBAM_${MbamSeedId}`, string>>;

export function resolveMbamSeedRunBases(
    env: MbamSeedEnv,
    fallbackBase: string
): Record<MbamSeedId, string> {
    return {
        A: resolveSeedBase(env.VITE_WEBVIEW_RUN_BASE_MBAM_A, fallbackBase),
        B: resolveSeedBase(env.VITE_WEBVIEW_RUN_BASE_MBAM_B, fallbackBase),
        C: resolveSeedBase(env.VITE_WEBVIEW_RUN_BASE_MBAM_C, fallbackBase),
    };
}

function resolveSeedBase(value: string | undefined, fallbackBase: string): string {
    const clean = value?.trim();
    if (clean) return clean;
    return fallbackBase;
}
