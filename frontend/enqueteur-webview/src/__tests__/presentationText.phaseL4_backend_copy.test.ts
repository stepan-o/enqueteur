import { afterEach, describe, expect, it } from "vitest";

import { resolvePresentationField, resolvePresentationFieldList, resolvePresentationText } from "../app/presentationText";
import { setLocale } from "../i18n";

afterEach(() => {
    setLocale("en");
});

describe("Phase L4 backend presentation text localization", () => {
    it("prefers localized key for room/case presentation fields", () => {
        setLocale("fr");

        const resolved = resolvePresentationText({
            text: "MBAM Lobby",
            textKey: "mbam.room.MBAM_LOBBY.label",
        });

        expect(resolved).toBe("Hall MBAM");
    });

    it("falls back to raw backend text when key is not migrated", () => {
        setLocale("fr");

        const resolved = resolvePresentationText({
            text: "Legacy backend clue line.",
            textKey: "mbam.clue.not.migrated",
        });

        expect(resolved).toBe("Legacy backend clue line.");
    });

    it("resolves known_state field keys and list keys with raw fallback", () => {
        setLocale("en");

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

        expect(resolvePresentationField(knownState, "item")).toBe("filter coffee");
        expect(resolvePresentationText({
            text: "17h58",
            textKey: "mbam.clue.torn_note.a.option.time_1758",
        })).toBe("17:58");
        expect(resolvePresentationFieldList(knownState, "torn_note_options", "torn_note_option_keys")).toEqual([
            "fallback only",
            "delivery",
            "17:58",
        ]);
    });
});
