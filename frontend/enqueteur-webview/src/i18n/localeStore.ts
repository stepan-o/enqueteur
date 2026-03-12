import { DEFAULT_LOCALE, normalizeLocale, type AppLocale } from "./locale";

export const LOCALE_STORAGE_KEY = "enqueteur.locale";

export type LocaleState = {
    locale: AppLocale;
    source: "persisted" | "browser" | "default";
};

export type LocaleSubscriber = (state: LocaleState) => void;

export class LocaleStore {
    private state: LocaleState;
    private readonly subscribers = new Set<LocaleSubscriber>();

    constructor(initialLocale?: AppLocale) {
        this.state = initialLocale
            ? { locale: initialLocale, source: "default" }
            : resolveInitialLocaleState();
    }

    getState(): LocaleState {
        return this.state;
    }

    getLocale(): AppLocale {
        return this.state.locale;
    }

    setLocale(nextLocale: AppLocale): void {
        writePersistedLocale(nextLocale);
        if (nextLocale === this.state.locale) return;
        this.state = {
            locale: nextLocale,
            source: "persisted",
        };
        this.emit();
    }

    subscribe(cb: LocaleSubscriber): () => void {
        this.subscribers.add(cb);
        cb(this.state);
        return () => {
            this.subscribers.delete(cb);
        };
    }

    private emit(): void {
        for (const cb of this.subscribers) cb(this.state);
    }
}

const SHARED_LOCALE_STORE = new LocaleStore();

export function getSharedLocaleStore(): LocaleStore {
    return SHARED_LOCALE_STORE;
}

function resolveInitialLocaleState(): LocaleState {
    const persistedLocale = readPersistedLocale();
    if (persistedLocale) {
        return {
            locale: persistedLocale,
            source: "persisted",
        };
    }

    const browserLocale = readBrowserLocale();
    if (browserLocale) {
        return {
            locale: browserLocale,
            source: "browser",
        };
    }

    return {
        locale: DEFAULT_LOCALE,
        source: "default",
    };
}

function readPersistedLocale(): AppLocale | null {
    if (typeof window === "undefined") return null;
    try {
        const raw = window.localStorage.getItem(LOCALE_STORAGE_KEY);
        const normalized = normalizeLocale(raw);
        if (normalized) return normalized;
        if (raw) {
            window.localStorage.removeItem(LOCALE_STORAGE_KEY);
        }
    } catch {
        return null;
    }
    return null;
}

function readBrowserLocale(): AppLocale | null {
    if (typeof navigator === "undefined") return null;
    const candidateLocales: string[] = [];
    if (Array.isArray(navigator.languages)) {
        candidateLocales.push(...navigator.languages);
    }
    if (typeof navigator.language === "string") {
        candidateLocales.push(navigator.language);
    }

    for (const candidate of candidateLocales) {
        const normalized = normalizeLocale(candidate);
        if (normalized) return normalized;
    }
    return null;
}

function writePersistedLocale(locale: AppLocale): void {
    if (typeof window === "undefined") return;
    try {
        window.localStorage.setItem(LOCALE_STORAGE_KEY, locale);
    } catch {
        // Ignore persistence failures; locale still updates in-memory.
    }
}
