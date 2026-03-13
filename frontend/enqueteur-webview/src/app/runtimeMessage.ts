import { getLocale, translate, type TranslationLookupKey, type TranslationParams } from "../i18n";

export type RuntimeMessageResolveInput = {
    message?: string | null;
    messageKey?: string | null;
    messageParams?: unknown;
    fallbackMessage?: string;
    fallbackKey?: string | null;
    fallbackParams?: unknown;
};

export function resolveRuntimeMessage(input: RuntimeMessageResolveInput): string {
    const primary = translateIfKnown(input.messageKey, input.messageParams);
    if (primary) return primary;

    const fallbackByKey = translateIfKnown(input.fallbackKey, input.fallbackParams);
    if (fallbackByKey) return fallbackByKey;

    const legacyMessage = normalizeMessage(input.message);
    if (legacyMessage) return legacyMessage;

    return normalizeMessage(input.fallbackMessage) ?? "Message unavailable.";
}

export function buildRuntimeMessageKey(prefix: string, code: string): string {
    const token = normalizeToken(code);
    const normalizedPrefix = prefix.trim();
    return normalizedPrefix ? `${normalizedPrefix}.${token}` : token;
}

function translateIfKnown(key: string | null | undefined, params: unknown): string | null {
    const normalizedKey = normalizeMessage(key);
    if (!normalizedKey) return null;

    const translated = translate(
        getLocale(),
        normalizedKey as TranslationLookupKey,
        normalizeParams(params)
    );
    if (translated === `[${normalizedKey}]`) return null;
    return translated;
}

function normalizeParams(value: unknown): TranslationParams {
    if (!value || typeof value !== "object" || Array.isArray(value)) return {};
    const params: TranslationParams = {};
    for (const [key, entry] of Object.entries(value)) {
        params[key] = normalizeParamValue(entry);
    }
    return params;
}

function normalizeParamValue(value: unknown): string | number | boolean | null | undefined {
    if (
        value === null ||
        value === undefined ||
        typeof value === "string" ||
        typeof value === "number" ||
        typeof value === "boolean"
    ) {
        return value;
    }
    try {
        return JSON.stringify(value);
    } catch {
        return String(value);
    }
}

function normalizeMessage(value: string | null | undefined): string | null {
    if (typeof value !== "string") return null;
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
}

function normalizeToken(value: string): string {
    const normalized = value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
    return normalized || "unknown";
}
