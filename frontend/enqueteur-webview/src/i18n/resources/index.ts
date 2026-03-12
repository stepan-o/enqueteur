import type { AppLocale } from "../locale";
import { EN_MESSAGES, type TranslationKey } from "./en";
import { FR_MESSAGES } from "./fr";

export type TranslationTable = Record<TranslationKey, string>;

export const TRANSLATION_RESOURCES: Record<AppLocale, Partial<TranslationTable>> = {
    en: EN_MESSAGES,
    fr: FR_MESSAGES,
};
