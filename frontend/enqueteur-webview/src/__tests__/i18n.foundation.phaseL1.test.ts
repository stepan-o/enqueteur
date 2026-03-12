import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LOCALE_STORAGE_KEY, LocaleStore, translate } from "../i18n";

function mockNavigatorLocales(languages: string[], language: string): void {
    vi.spyOn(window.navigator, "languages", "get").mockReturnValue(languages);
    vi.spyOn(window.navigator, "language", "get").mockReturnValue(language);
}

describe("Phase L1 i18n foundation", () => {
    const originalLocalStorage = Object.getOwnPropertyDescriptor(window, "localStorage");
    let storageState: Record<string, string>;

    const mockStorage: Storage = {
        get length() {
            return Object.keys(storageState).length;
        },
        clear(): void {
            storageState = {};
        },
        getItem(key: string): string | null {
            return Object.prototype.hasOwnProperty.call(storageState, key) ? storageState[key] : null;
        },
        key(index: number): string | null {
            const keys = Object.keys(storageState);
            return keys[index] ?? null;
        },
        removeItem(key: string): void {
            delete storageState[key];
        },
        setItem(key: string, value: string): void {
            storageState[key] = value;
        },
    };

    beforeEach(() => {
        storageState = {};
        Object.defineProperty(window, "localStorage", {
            configurable: true,
            value: mockStorage,
        });
    });

    afterEach(() => {
        vi.restoreAllMocks();
        if (originalLocalStorage) {
            Object.defineProperty(window, "localStorage", originalLocalStorage);
        }
    });

    it("prioritizes persisted locale over browser locale", () => {
        window.localStorage.setItem(LOCALE_STORAGE_KEY, "fr-CA");
        mockNavigatorLocales(["en-US"], "en-US");

        const store = new LocaleStore();

        expect(store.getLocale()).toBe("fr");
        expect(store.getState().source).toBe("persisted");
    });

    it("uses browser locale when no persisted locale exists", () => {
        mockNavigatorLocales(["fr-CA", "en-US"], "fr-CA");

        const store = new LocaleStore();

        expect(store.getLocale()).toBe("fr");
        expect(store.getState().source).toBe("browser");
    });

    it("defaults to english when browser locale is unsupported", () => {
        mockNavigatorLocales(["es-ES"], "es-ES");

        const store = new LocaleStore();

        expect(store.getLocale()).toBe("en");
        expect(store.getState().source).toBe("default");
    });

    it("persists locale updates to localStorage", () => {
        const store = new LocaleStore("en");

        store.setLocale("fr");

        expect(store.getLocale()).toBe("fr");
        expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBe("fr");
    });

    it("interpolates parameters and falls back to english when locale key is missing", () => {
        expect(
            translate("fr", "flow.caseSelect.defaultDemoRoute", { title: "Route A" })
        ).toBe("Parcours demo par defaut: Route A");
        expect(translate("fr", "i18n.seed.onlyEnglish")).toBe("English-only seed fallback.");
    });

    it("returns a key marker when translation is missing in every locale", () => {
        expect(translate("fr", "missing.translation.key")).toBe("[missing.translation.key]");
    });
});
