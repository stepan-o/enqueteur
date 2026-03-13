import { describe, expect, it } from "vitest";

import { resolveRuntimeMessage } from "../app/runtimeMessage";
import { setLocale } from "../i18n";
import { BILINGUAL_LOCALES, trFor, useLocaleFixture } from "./testUtils/localeTestUtils";

const tr = {
    en: trFor("en"),
    fr: trFor("fr"),
};

useLocaleFixture("en");

describe("Phase L3 runtime message localization contract", () => {
    it.each(BILINGUAL_LOCALES)("localizes by message_key when key is known (%s)", (locale) => {
        setLocale(locale);

        const resolved = resolveRuntimeMessage({
            messageKey: "launch.error.unsupported_case",
            message: "Unsupported case in this build.",
            messageParams: { code: "UNSUPPORTED_CASE" },
        });

        expect(resolved).toBe(tr[locale]("launch.error.unsupported_case"));
    });

    it.each(BILINGUAL_LOCALES)("falls back to legacy message when key is unknown (%s)", (locale) => {
        setLocale(locale);

        const resolved = resolveRuntimeMessage({
            messageKey: "live.warn.not_migrated_yet",
            message: "Raw backend warning for migration gap.",
            messageParams: { code: "NOT_MIGRATED_YET" },
        });

        expect(resolved).toBe("Raw backend warning for migration gap.");
    });

    it.each(BILINGUAL_LOCALES)("uses fallback key when primary key is absent (%s)", (locale) => {
        setLocale(locale);

        const resolved = resolveRuntimeMessage({
            message: "Launch failed.",
            fallbackKey: "launch.error.launch_failed",
            fallbackParams: { code: "LAUNCH_FAILED" },
        });

        expect(resolved).toBe(tr[locale]("launch.error.launch_failed"));
    });

    it("returns a safe default when key and message are both unavailable", () => {
        const resolved = resolveRuntimeMessage({});

        expect(resolved).toBe("Message unavailable.");
    });
});
