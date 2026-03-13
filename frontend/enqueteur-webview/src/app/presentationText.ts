import { getLocale, translate, type TranslationLookupKey, type TranslationParams } from "../i18n";

type ResolvePresentationTextInput = {
    text?: unknown;
    textKey?: unknown;
    textParams?: unknown;
    fallbackText?: string | null;
};

export function resolvePresentationText(input: ResolvePresentationTextInput): string | null {
    const translated = translateIfKnown(input.textKey, input.textParams);
    if (translated) return translated;

    const fallback = normalizeString(input.text);
    if (fallback) return fallback;

    return normalizeString(input.fallbackText);
}

export function resolvePresentationField(
    source: Record<string, unknown>,
    field: string
): string | null {
    return resolvePresentationText({
        text: source[field],
        textKey: source[`${field}_key`],
        textParams: source[`${field}_params`],
    });
}

export function resolvePresentationFieldList(
    source: Record<string, unknown>,
    field: string,
    keyField: string = `${field}_keys`
): string[] | null {
    const values = asStringArray(source[field]);
    const keys = asStringArray(source[keyField]);
    if (keys.length > 0) {
        const resolved = keys
            .map((key, idx) => resolvePresentationText({
                text: values[idx],
                textKey: key,
            }))
            .filter((row): row is string => Boolean(row));
        if (resolved.length > 0) return resolved;
    }
    if (values.length > 0) return values;
    return null;
}

function translateIfKnown(key: unknown, params: unknown): string | null {
    const normalizedKey = normalizeString(key);
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
    const out: TranslationParams = {};
    for (const [key, entry] of Object.entries(value as Record<string, unknown>)) {
        out[key] = normalizeParamValue(entry);
    }
    return out;
}

function normalizeParamValue(value: unknown): string | number | boolean | null | undefined {
    if (
        value === null
        || value === undefined
        || typeof value === "string"
        || typeof value === "number"
        || typeof value === "boolean"
    ) {
        return value;
    }
    try {
        return JSON.stringify(value);
    } catch {
        return String(value);
    }
}

function normalizeString(value: unknown): string | null {
    if (typeof value !== "string") return null;
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
}

function asStringArray(value: unknown): string[] {
    if (!Array.isArray(value)) return [];
    return value
        .map((row) => normalizeString(row))
        .filter((row): row is string => row !== null);
}
