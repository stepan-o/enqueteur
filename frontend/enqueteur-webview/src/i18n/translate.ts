import type { AppLocale } from "./locale";
import { EN_MESSAGES, type TranslationKey } from "./resources/en";
import { TRANSLATION_RESOURCES } from "./resources";

export type TranslationLookupKey = TranslationKey | (string & {});

export type TranslationParams = Record<string, string | number | boolean | null | undefined>;

export type TranslateFn = (key: TranslationLookupKey, params?: TranslationParams) => string;

const INTERPOLATION_PATTERN = /\{([a-zA-Z0-9_]+)\}/g;

export function translate(
    locale: AppLocale,
    key: TranslationLookupKey,
    params: TranslationParams = {}
): string {
    const localeMap = TRANSLATION_RESOURCES[locale] as Record<string, string | undefined>;
    const fallbackMap = EN_MESSAGES as Record<string, string | undefined>;
    const template = localeMap[key] ?? fallbackMap[key] ?? `[${key}]`;
    return interpolateTemplate(template, params);
}

export function createTranslator(getLocale: () => AppLocale): TranslateFn {
    return (key, params) => translate(getLocale(), key, params);
}

function interpolateTemplate(template: string, params: TranslationParams): string {
    return template.replace(INTERPOLATION_PATTERN, (_match, token: string) => {
        const value = params[token];
        if (value === null || value === undefined) return `{${token}}`;
        return String(value);
    });
}
