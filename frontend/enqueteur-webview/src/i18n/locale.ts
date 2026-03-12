export const SUPPORTED_LOCALES = ["en", "fr"] as const;

export type AppLocale = (typeof SUPPORTED_LOCALES)[number];

export const DEFAULT_LOCALE: AppLocale = "en";

export function isSupportedLocale(value: unknown): value is AppLocale {
    return value === "en" || value === "fr";
}

export function normalizeLocale(value: unknown): AppLocale | null {
    if (typeof value !== "string") return null;
    const normalized = value.trim().toLowerCase();
    if (!normalized) return null;
    const primaryTag = normalized.split(/[-_]/)[0] ?? normalized;
    if (isSupportedLocale(primaryTag)) return primaryTag;
    return null;
}
