import type { AppLocale } from "./locale";
import { createTranslator, type TranslateFn, type TranslationLookupKey, type TranslationParams } from "./translate";
import { getSharedLocaleStore } from "./localeStore";

const sharedTranslator = createTranslator(() => getSharedLocaleStore().getLocale());

export function t(key: TranslationLookupKey, params?: TranslationParams): string {
    return sharedTranslator(key, params);
}

export function getLocale(): AppLocale {
    return getSharedLocaleStore().getLocale();
}

export function setLocale(locale: AppLocale): void {
    getSharedLocaleStore().setLocale(locale);
}

export function createScopedTranslator(getLocaleValue: () => AppLocale): TranslateFn {
    return createTranslator(getLocaleValue);
}

export type { AppLocale } from "./locale";
export { DEFAULT_LOCALE, SUPPORTED_LOCALES, normalizeLocale, isSupportedLocale } from "./locale";
export { LocaleStore, LOCALE_STORAGE_KEY, getSharedLocaleStore, type LocaleState } from "./localeStore";
export type { TranslateFn, TranslationLookupKey, TranslationParams } from "./translate";
export { translate } from "./translate";
export type { TranslationKey } from "./resources/en";
