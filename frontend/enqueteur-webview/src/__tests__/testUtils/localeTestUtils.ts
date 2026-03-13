import { afterEach, beforeEach } from "vitest";

import {
    setLocale,
    translate,
    type AppLocale,
    type TranslationLookupKey,
    type TranslationParams,
} from "../../i18n";

export const BILINGUAL_LOCALES: readonly AppLocale[] = ["en", "fr"] as const;

export function useLocaleFixture(defaultLocale: AppLocale = "en"): void {
    beforeEach(() => {
        setLocale(defaultLocale);
    });

    afterEach(() => {
        setLocale(defaultLocale);
    });
}

export function trFor(locale: AppLocale): (
    key: TranslationLookupKey,
    params?: TranslationParams
) => string {
    return (key, params) => translate(locale, key, params);
}
