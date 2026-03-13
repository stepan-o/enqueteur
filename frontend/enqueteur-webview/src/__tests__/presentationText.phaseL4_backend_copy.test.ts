import { describe, expect, it } from "vitest";

import { resolvePresentationField, resolvePresentationFieldList, resolvePresentationText } from "../app/presentationText";
import { setLocale } from "../i18n";
import { BILINGUAL_LOCALES, trFor, useLocaleFixture } from "./testUtils/localeTestUtils";

const tr = {
    en: trFor("en"),
    fr: trFor("fr"),
};

useLocaleFixture("en");

describe("Phase L4 backend presentation text localization", () => {
    it.each(BILINGUAL_LOCALES)("prefers localized key for room/case presentation fields (%s)", (locale) => {
        setLocale(locale);

        const resolved = resolvePresentationText({
            text: "MBAM Lobby",
            textKey: "mbam.room.MBAM_LOBBY.label",
        });

        expect(resolved).toBe(tr[locale]("mbam.room.MBAM_LOBBY.label"));
    });

    it("falls back to raw backend text when key is not migrated", () => {
        setLocale("fr");

        const resolved = resolvePresentationText({
            text: "Legacy backend clue line.",
            textKey: "mbam.clue.not.migrated",
        });

        expect(resolved).toBe("Legacy backend clue line.");
    });

    it.each(BILINGUAL_LOCALES)("resolves known_state field/list keys with raw fallback (%s)", (locale) => {
        setLocale(locale);

        const knownState = {
            item: "cafe filtre",
            item_key: "mbam.clue.receipt.item.a",
            torn_note_options: ["fallback only", "delivery", "17h58"],
            torn_note_option_keys: [
                "mbam.clue.not_migrated.option_0",
                "mbam.clue.torn_note.a.option.livraison",
                "mbam.clue.torn_note.a.option.time_1758",
            ],
        } as const;

        expect(resolvePresentationField(knownState, "item")).toBe(tr[locale]("mbam.clue.receipt.item.a"));
        expect(resolvePresentationText({
            text: "17h58",
            textKey: "mbam.clue.torn_note.a.option.time_1758",
        })).toBe(tr[locale]("mbam.clue.torn_note.a.option.time_1758"));
        expect(resolvePresentationFieldList(knownState, "torn_note_options", "torn_note_option_keys")).toEqual([
            "fallback only",
            tr[locale]("mbam.clue.torn_note.a.option.livraison"),
            tr[locale]("mbam.clue.torn_note.a.option.time_1758"),
        ]);
    });
});
