import { afterEach, describe, expect, it } from "vitest";

import { resolveRuntimeMessage } from "../app/runtimeMessage";
import { setLocale } from "../i18n";

afterEach(() => {
    setLocale("en");
});

describe("Phase L3 runtime message localization contract", () => {
    it("localizes by message_key when key is known", () => {
        setLocale("fr");

        const resolved = resolveRuntimeMessage({
            messageKey: "launch.error.unsupported_case",
            message: "Unsupported case in this build.",
            messageParams: { code: "UNSUPPORTED_CASE" },
        });

        expect(resolved).toBe("Ce dossier n'est pas disponible dans cette version.");
    });

    it("falls back to legacy message when key is unknown", () => {
        setLocale("fr");

        const resolved = resolveRuntimeMessage({
            messageKey: "live.warn.not_migrated_yet",
            message: "Raw backend warning for migration gap.",
            messageParams: { code: "NOT_MIGRATED_YET" },
        });

        expect(resolved).toBe("Raw backend warning for migration gap.");
    });

    it("uses fallback key when primary key is absent", () => {
        setLocale("fr");

        const resolved = resolveRuntimeMessage({
            message: "Launch failed.",
            fallbackKey: "launch.error.launch_failed",
            fallbackParams: { code: "LAUNCH_FAILED" },
        });

        expect(resolved).toBe("Le lancement du dossier a echoue dans le service backend.");
    });

    it("returns a safe default when key and message are both unavailable", () => {
        const resolved = resolveRuntimeMessage({});

        expect(resolved).toBe("Message unavailable.");
    });
});
