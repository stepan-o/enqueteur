// src/ui/notebookPanel.ts
import type { KvpInvestigationState, WorldState, WorldStore } from "../state/worldStore";
import {
    buildMbamOnboardingView,
    buildMbamPlaytestPathView,
    getMbamObjectGuide,
    hintMbamAction,
    labelMbamAction,
    labelMbamContradictionEdge,
    listMbamObjectGuides,
} from "./mbamOnboarding";

export type NotebookPanelHandle = {
    root: HTMLElement;
    setPresentationProfile?: (profile: "demo" | "playtest" | "dev") => void;
};

export type MinigameSubmitRequest = {
    minigameId: "MG1" | "MG2" | "MG3" | "MG4";
    targetId: string;
    answer: Record<string, unknown>;
    tick: number;
};

export type MinigameSubmitResult = {
    status: "submitted" | "accepted" | "blocked" | "invalid" | "unavailable" | "error";
    code: string;
    summary?: string;
};

export type MinigameSubmitDispatcher = (
    request: MinigameSubmitRequest
) => Promise<MinigameSubmitResult> | MinigameSubmitResult;

export type NotebookPanelOpts = {
    dispatchMinigameSubmit?: MinigameSubmitDispatcher;
    canDispatchMinigameSubmit?: () => boolean;
    allowLocalEvaluation?: () => boolean;
    presentationProfile?: "demo" | "playtest" | "dev";
};

type MinigameUiState = {
    answers: Record<string, string>;
    attempts: number;
    feedback: string | null;
    passed: boolean | null;
};

type LearningProjection = NonNullable<WorldState["dialogue"]>["learning"];
type ProjectedMinigameState = {
    attempt_count: number;
    completed: boolean;
    score: number;
    max_score: number;
    pass_score_required?: number;
    gate_open?: boolean;
    gate_code?: string;
    retry_recommended?: boolean;
    status: string;
};

type BadgeLogRowSource = {
    badge_id: string;
    time: string;
    door: string;
};

type Mg2Source = {
    entries: BadgeLogRowSource[];
};

type Mg4Source = {
    variantId: string;
    prompt: string;
    options: string[];
};

type ConfirmationStrengthMode = "explicit" | "compact";

const EVIDENCE_LABELS: Record<string, string> = {
    E1_TORN_NOTE: "E1 Torn Note",
    E2_CAFE_RECEIPT: "E2 Cafe Receipt",
    E3_METHOD_TRACE: "E3 Lanyard Fiber/Sticker",
};

const FACT_LABELS: Record<string, string> = {
    N1: "Missing item discovered (~18h05)",
    N2: "Staff badge required for corridor",
    N3: "Badge log entry (17h58)",
    N4: "Cafe receipt timestamp (17h52)",
    N5: "Witness clothing description",
    N6: "Torn note directional/time clue",
    N7: "Display case latch/lock clue",
    N8: "Drop location clue",
};

const FACT_TIMELINE_ORDER: string[] = ["N4", "N3", "N1", "N5", "N6", "N7", "N8", "N2"];

const OBJECT_LABELS: Record<string, string> = {
    O1_DISPLAY_CASE: "Display Case",
    O2_MEDALLION: "Medallion",
    O3_WALL_LABEL: "Wall Label",
    O4_BENCH: "Bench",
    O5_VISITOR_LOGBOOK: "Visitor Logbook",
    O6_BADGE_TERMINAL: "Badge Terminal",
    O7_SECURITY_BINDER: "Security Binder",
    O8_KEYPAD_DOOR: "Keypad Door",
    O9_RECEIPT_PRINTER: "Receipt Printer",
    O10_BULLETIN_BOARD: "Bulletin Board",
};

export function mountNotebookPanel(store: WorldStore, opts: NotebookPanelOpts = {}): NotebookPanelHandle {
    const root = document.createElement("div");
    root.className = "notebook-root";

    const panel = document.createElement("div");
    panel.className = "notebook-panel";
    root.appendChild(panel);

    let lastState: WorldState | null = null;
    let mg1State: MinigameUiState = {
        answers: { title: "", date: "" },
        attempts: 0,
        feedback: null,
        passed: null,
    };
    let mg3State: MinigameUiState = {
        answers: { time: "", item: "" },
        attempts: 0,
        feedback: null,
        passed: null,
    };
    let mg2State: MinigameUiState = {
        answers: { badge_id: "", time: "" },
        attempts: 0,
        feedback: null,
        passed: null,
    };
    let mg4State: MinigameUiState = {
        answers: { slot1: "", slot2: "", slot3: "" },
        attempts: 0,
        feedback: null,
        passed: null,
    };
    let presentationProfile: "demo" | "playtest" | "dev" = opts.presentationProfile ?? "playtest";

    const canDispatchLiveMinigame = (): boolean => {
        if (!opts.dispatchMinigameSubmit) return false;
        if (opts.canDispatchMinigameSubmit) return opts.canDispatchMinigameSubmit();
        return true;
    };

    const canUseLocalEvaluationFallback = (): boolean => {
        if (opts.allowLocalEvaluation) return opts.allowLocalEvaluation();
        return true;
    };

    const applyLiveMinigameResult = (
        state: MinigameUiState,
        result: MinigameSubmitResult
    ): MinigameUiState => {
        const attemptsDelta = result.status === "unavailable" ? 0 : 1;
        return {
            ...state,
            attempts: state.attempts + attemptsDelta,
            feedback: result.summary ?? `${result.code}`,
            passed: result.status === "accepted" ? true : result.status === "invalid" || result.status === "blocked" ? false : null,
        };
    };

    const submitLiveMinigame = async (
        request: MinigameSubmitRequest
    ): Promise<MinigameSubmitResult> => {
        if (!opts.dispatchMinigameSubmit) {
            return {
                status: "unavailable",
                code: "live_dispatch_unavailable",
                summary: "Can't submit right now. Connection is not ready.",
            };
        }
        try {
            return await opts.dispatchMinigameSubmit(request);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : String(err);
            return {
                status: "error",
                code: "dispatch_error",
                summary: message,
            };
        }
    };

    const render = (): void => {
        panel.innerHTML = "";
        if (!lastState) {
            panel.style.display = "none";
            return;
        }
        panel.style.display = "block";

        const title = document.createElement("div");
        title.className = "notebook-title";
        title.textContent = "Case Notes";
        panel.appendChild(title);

        const investigation = lastState.investigation;
        if (!investigation) {
            renderInfo(panel, "Case notes are still loading.");
            return;
        }

        const onboarding = buildMbamOnboardingView(lastState);
        const playtestPath = buildMbamPlaytestPathView(lastState);
        const isDemoProfile = presentationProfile === "demo";
        renderSectionTitle(panel, "Case Brief");
        renderInfo(panel, onboarding.caseSummary);
        renderSectionTitle(panel, "Start Here");
        renderOnboardingSteps(panel, onboarding.steps);
        renderInfo(panel, `Current lead: ${onboarding.currentLead}`);
        if (!isDemoProfile) {
            renderSectionTitle(panel, playtestPath.title);
            renderOnboardingSteps(panel, playtestPath.steps);
            renderInfo(panel, playtestPath.currentMilestone);
            renderLines(panel, [
                ["Case", lastState.caseState?.case_id ?? "MBAM_01"],
                ["Seed", lastState.caseState?.seed ?? "-"],
                ["Truth epoch", String(investigation.truth_epoch)],
            ]);
        } else {
            renderLines(panel, [["Case", lastState.caseState?.case_id ?? "MBAM_01"]]);
        }

        renderSectionTitle(panel, "Key Object Leads");
        renderKeyObjectLeads(panel, investigation, isDemoProfile);

        renderSectionTitle(panel, "Evidence Tray");
        renderEvidenceTray(panel, investigation);

        renderSectionTitle(panel, "Known Facts");
        renderFactVisibility(panel, investigation);

        renderSectionTitle(panel, "Contradictions");
        renderContradictions(panel, lastState, investigation, isDemoProfile);

        renderSectionTitle(panel, "Timeline Clues");
        renderTimeline(panel, investigation);

        renderSectionTitle(panel, "Field Exercises");
        renderMinigames(panel, {
            isDemoProfile,
            state: lastState,
            investigation,
            mg1State,
            mg2State,
            mg3State,
            mg4State,
            onMg1Answer: (field, value) => {
                mg1State = {
                    ...mg1State,
                    answers: {
                        ...mg1State.answers,
                        [field]: value,
                    },
                };
            },
            onMg1Submit: (source) => {
                if (!canDispatchLiveMinigame()) {
                    if (!canUseLocalEvaluationFallback()) {
                        mg1State = applyLiveMinigameResult(mg1State, {
                            status: "unavailable",
                            code: "live_dispatch_unavailable",
                            summary: "Can't submit right now. Connection is not ready.",
                        });
                        render();
                        return;
                    }
                    mg1State = evaluateMg1(mg1State, source, currentConfirmationStrength(lastState));
                    render();
                    return;
                }
                mg1State = {
                    ...mg1State,
                    feedback: "Submitting answer...",
                    passed: null,
                };
                render();
                const tick = lastState?.tick ?? 0;
                void submitLiveMinigame({
                    minigameId: "MG1",
                    targetId: "O3_WALL_LABEL",
                    answer: {
                        title: source.title,
                        date: source.date,
                    },
                    tick,
                }).then((result) => {
                    mg1State = applyLiveMinigameResult(mg1State, result);
                    render();
                });
            },
            onMg1Reset: () => {
                mg1State = {
                    answers: { title: "", date: "" },
                    attempts: mg1State.attempts,
                    feedback: null,
                    passed: null,
                };
                render();
            },
            onMg2Answer: (field, value) => {
                mg2State = {
                    ...mg2State,
                    answers: {
                        ...mg2State.answers,
                        [field]: value,
                    },
                };
            },
            onMg2Submit: (source) => {
                if (!canDispatchLiveMinigame()) {
                    if (!canUseLocalEvaluationFallback()) {
                        mg2State = applyLiveMinigameResult(mg2State, {
                            status: "unavailable",
                            code: "live_dispatch_unavailable",
                            summary: "Can't submit right now. Connection is not ready.",
                        });
                        render();
                        return;
                    }
                    mg2State = evaluateMg2(mg2State, source, currentConfirmationStrength(lastState));
                    render();
                    return;
                }
                mg2State = {
                    ...mg2State,
                    feedback: "Submitting answer...",
                    passed: null,
                };
                render();
                const tick = lastState?.tick ?? 0;
                void submitLiveMinigame({
                    minigameId: "MG2",
                    targetId: "O6_BADGE_TERMINAL",
                    answer: {
                        selected_entry_id: source.entries.find((row) => row.badge_id === mg2State.answers.badge_id)?.badge_id
                            ?? mg2State.answers.badge_id,
                        time_value: mg2State.answers.time,
                    },
                    tick,
                }).then((result) => {
                    mg2State = applyLiveMinigameResult(mg2State, result);
                    render();
                });
            },
            onMg2Reset: () => {
                mg2State = {
                    answers: { badge_id: "", time: "" },
                    attempts: mg2State.attempts,
                    feedback: null,
                    passed: null,
                };
                render();
            },
            onMg3Answer: (field, value) => {
                mg3State = {
                    ...mg3State,
                    answers: {
                        ...mg3State.answers,
                        [field]: value,
                    },
                };
            },
            onMg3Submit: (source) => {
                if (!canDispatchLiveMinigame()) {
                    if (!canUseLocalEvaluationFallback()) {
                        mg3State = applyLiveMinigameResult(mg3State, {
                            status: "unavailable",
                            code: "live_dispatch_unavailable",
                            summary: "Can't submit right now. Connection is not ready.",
                        });
                        render();
                        return;
                    }
                    mg3State = evaluateMg3(mg3State, source, currentConfirmationStrength(lastState));
                    render();
                    return;
                }
                mg3State = {
                    ...mg3State,
                    feedback: "Submitting answer...",
                    passed: null,
                };
                render();
                const tick = lastState?.tick ?? 0;
                const answer: Record<string, unknown> = {
                    time_value: mg3State.answers.time,
                    item_value: mg3State.answers.item,
                };
                if (source.receiptId) {
                    answer.receipt_id = source.receiptId;
                }
                void submitLiveMinigame({
                    minigameId: "MG3",
                    targetId: "O9_RECEIPT_PRINTER",
                    answer,
                    tick,
                }).then((result) => {
                    mg3State = applyLiveMinigameResult(mg3State, result);
                    render();
                });
            },
            onMg3Reset: () => {
                mg3State = {
                    answers: { time: "", item: "" },
                    attempts: mg3State.attempts,
                    feedback: null,
                    passed: null,
                };
                render();
            },
            onMg4Answer: (field, value) => {
                mg4State = {
                    ...mg4State,
                    answers: {
                        ...mg4State.answers,
                        [field]: value,
                    },
                };
            },
            onMg4Submit: (source) => {
                if (!canDispatchLiveMinigame()) {
                    if (!canUseLocalEvaluationFallback()) {
                        mg4State = applyLiveMinigameResult(mg4State, {
                            status: "unavailable",
                            code: "live_dispatch_unavailable",
                            summary: "Can't submit right now. Connection is not ready.",
                        });
                        render();
                        return;
                    }
                    mg4State = evaluateMg4(mg4State, source, currentConfirmationStrength(lastState));
                    render();
                    return;
                }
                mg4State = {
                    ...mg4State,
                    feedback: "Submitting answer...",
                    passed: null,
                };
                render();
                const tick = lastState?.tick ?? 0;
                void submitLiveMinigame({
                    minigameId: "MG4",
                    targetId: "O4_BENCH",
                    answer: {
                        slot1: mg4State.answers.slot1,
                        slot2: mg4State.answers.slot2,
                        slot3: mg4State.answers.slot3,
                        variant_id: source.variantId,
                    },
                    tick,
                }).then((result) => {
                    mg4State = applyLiveMinigameResult(mg4State, result);
                    render();
                });
            },
            onMg4Reset: () => {
                mg4State = {
                    answers: { slot1: "", slot2: "", slot3: "" },
                    attempts: mg4State.attempts,
                    feedback: null,
                    passed: null,
                };
                render();
            },
        });
    };

    store.subscribe((state) => {
        lastState = state;
        render();
    });

    return {
        root,
        setPresentationProfile: (profile) => {
            presentationProfile = profile;
            render();
        },
    };
}

function currentConfirmationStrength(state: WorldState | null): ConfirmationStrengthMode {
    const mode = state?.dialogue?.learning?.scaffolding_policy?.confirmation_strength;
    return mode === "compact" ? "compact" : "explicit";
}

type MinigameRenderOpts = {
    isDemoProfile: boolean;
    state: WorldState;
    investigation: KvpInvestigationState;
    mg1State: MinigameUiState;
    mg2State: MinigameUiState;
    mg3State: MinigameUiState;
    mg4State: MinigameUiState;
    onMg1Answer: (field: "title" | "date", value: string) => void;
    onMg1Submit: (source: { title: string; date: string }) => void;
    onMg1Reset: () => void;
    onMg2Answer: (field: "badge_id" | "time", value: string) => void;
    onMg2Submit: (source: Mg2Source) => void;
    onMg2Reset: () => void;
    onMg3Answer: (field: "time" | "item", value: string) => void;
    onMg3Submit: (source: { time: string; item: string; receiptId?: string }) => void;
    onMg3Reset: () => void;
    onMg4Answer: (field: "slot1" | "slot2" | "slot3", value: string) => void;
    onMg4Submit: (source: Mg4Source) => void;
    onMg4Reset: () => void;
};

function renderMinigames(panel: HTMLElement, opts: MinigameRenderOpts): void {
    const objectRows = new Map(opts.investigation.objects.map((row) => [row.object_id, row]));
    const labelKnownState = objectRows.get("O3_WALL_LABEL")?.known_state ?? {};
    const badgeKnownState = objectRows.get("O6_BADGE_TERMINAL")?.known_state ?? {};
    const receiptKnownState = objectRows.get("O9_RECEIPT_PRINTER")?.known_state ?? {};
    const benchKnownState = objectRows.get("O4_BENCH")?.known_state ?? {};
    const learning = opts.state.dialogue?.learning ?? null;
    const mgRows = new Map((learning?.minigames ?? []).map((row) => [row.minigame_id, row]));

    const mg2Source = parseMg2Source(badgeKnownState);
    const mg4Source = parseMg4Source(benchKnownState);

    renderMg1Widget(panel, {
        isDemoProfile: opts.isDemoProfile,
        source:
            typeof labelKnownState.title === "string" && typeof labelKnownState.date === "string"
                ? { title: labelKnownState.title, date: labelKnownState.date }
                : null,
        state: opts.mg1State,
        projected: mgRows.get("MG1_LABEL_READING"),
        learning,
        onAnswer: opts.onMg1Answer,
        onSubmit: opts.onMg1Submit,
        onReset: opts.onMg1Reset,
    });

    renderMg2Widget(panel, {
        isDemoProfile: opts.isDemoProfile,
        source: mg2Source,
        state: opts.mg2State,
        projected: mgRows.get("MG2_BADGE_LOG"),
        learning,
        onAnswer: opts.onMg2Answer,
        onSubmit: opts.onMg2Submit,
        onReset: opts.onMg2Reset,
    });

    renderMg3Widget(panel, {
        isDemoProfile: opts.isDemoProfile,
        source: resolveMg3Source(receiptKnownState),
        state: opts.mg3State,
        projected: mgRows.get("MG3_RECEIPT_READING"),
        learning,
        onAnswer: opts.onMg3Answer,
        onSubmit: opts.onMg3Submit,
        onReset: opts.onMg3Reset,
    });

    renderMg4Widget(panel, {
        isDemoProfile: opts.isDemoProfile,
        source: mg4Source,
        state: opts.mg4State,
        projected: mgRows.get("MG4_TORN_NOTE_RECONSTRUCTION"),
        learning,
        onAnswer: opts.onMg4Answer,
        onSubmit: opts.onMg4Submit,
        onReset: opts.onMg4Reset,
    });
}

function parseMg2Source(knownState: Record<string, unknown>): Mg2Source | null {
    const raw = knownState.log_entries;
    if (!Array.isArray(raw)) return null;
    const entries: BadgeLogRowSource[] = [];
    for (const row of raw) {
        if (!row || typeof row !== "object") continue;
        const badgeId = (row as { badge_id?: unknown }).badge_id;
        const time = (row as { time?: unknown }).time;
        const door = (row as { door?: unknown }).door;
        if (typeof badgeId !== "string" || typeof time !== "string" || typeof door !== "string") {
            continue;
        }
        entries.push({ badge_id: badgeId, time, door });
    }
    return entries.length > 0 ? { entries } : null;
}

function parseMg4Source(knownState: Record<string, unknown>): Mg4Source | null {
    const prompt = knownState.torn_note_prompt;
    const variantId = knownState.torn_note_variant_id;
    const rawOptions = knownState.torn_note_options;
    if (typeof prompt !== "string" || typeof variantId !== "string" || !Array.isArray(rawOptions)) {
        return null;
    }
    const options = rawOptions.filter((row): row is string => typeof row === "string" && row.length > 0);
    if (options.length < 3) return null;
    return { variantId, prompt, options };
}

function resolveMg3Source(knownState: Record<string, unknown>): {
    time: string;
    item: string;
    receiptId?: string;
} | null {
    const time = knownState.time;
    const item = knownState.item;
    if (typeof time !== "string" || typeof item !== "string") {
        return null;
    }
    const latestReceiptId = knownState.latest_receipt_id;
    if (typeof latestReceiptId === "string" && latestReceiptId.trim().length > 0) {
        return {
            time,
            item,
            receiptId: latestReceiptId,
        };
    }
    return { time, item };
}

function renderMg1Widget(
    panel: HTMLElement,
    opts: {
        isDemoProfile: boolean;
        source: { title: string; date: string } | null;
        state: MinigameUiState;
        projected: ProjectedMinigameState | undefined;
        learning: LearningProjection | null | undefined;
        onAnswer: (field: "title" | "date", value: string) => void;
        onSubmit: (source: { title: string; date: string }) => void;
        onReset: () => void;
    }
): void {
    const wrap = document.createElement("div");
    wrap.className = "notebook-minigame";
    panel.appendChild(wrap);

    const title = document.createElement("div");
    title.className = "notebook-minigame-title";
    title.textContent = "Wall Label Check (MG1)";
    wrap.appendChild(title);

    if (!opts.source) {
        renderMiniInfo(wrap, "Read the wall label first (O3) to unlock this exercise.");
        return;
    }

    renderMiniSource(wrap, `Cartel\nTitre: ${opts.source.title}\nDate: ${opts.source.date}`);
    renderProjectedStatus(wrap, opts.projected, opts.state, opts.isDemoProfile);
    renderScaffoldingHints(wrap, opts.learning, "MG1_LABEL_READING", opts.isDemoProfile);
    renderMiniInput(wrap, {
        label: "Title",
        value: opts.state.answers.title ?? "",
        placeholder: "Le ...",
        onChange: (value) => opts.onAnswer("title", value),
    });
    renderMiniInput(wrap, {
        label: "Date",
        value: opts.state.answers.date ?? "",
        placeholder: "1898",
        onChange: (value) => opts.onAnswer("date", value),
    });
    renderMiniActions(wrap, {
        canSubmit: opts.projected?.gate_open ?? true,
        onSubmit: () => opts.onSubmit(opts.source!),
        onReset: opts.onReset,
    });
    renderMiniFeedback(wrap, opts.state);
}

function renderMg2Widget(
    panel: HTMLElement,
    opts: {
        isDemoProfile: boolean;
        source: Mg2Source | null;
        state: MinigameUiState;
        projected: ProjectedMinigameState | undefined;
        learning: LearningProjection | null | undefined;
        onAnswer: (field: "badge_id" | "time", value: string) => void;
        onSubmit: (source: Mg2Source) => void;
        onReset: () => void;
    }
): void {
    const wrap = document.createElement("div");
    wrap.className = "notebook-minigame";
    panel.appendChild(wrap);

    const title = document.createElement("div");
    title.className = "notebook-minigame-title";
    title.textContent = "Badge Log Check (MG2)";
    wrap.appendChild(title);

    if (!opts.source) {
        renderMiniInfo(wrap, "Read badge logs first (O6) to unlock this exercise.");
        return;
    }
    const source = opts.source;

    renderMiniSource(
        wrap,
        `Journal des badges\n${source.entries.map((row) => `${row.badge_id} | ${row.time} | ${row.door}`).join("\n")}`
    );
    renderProjectedStatus(wrap, opts.projected, opts.state, opts.isDemoProfile);
    renderScaffoldingHints(wrap, opts.learning, "MG2_BADGE_LOG", opts.isDemoProfile);
    renderMiniSelect(wrap, {
        label: "Important entry",
        value: opts.state.answers.badge_id ?? "",
        options: source.entries.map((row) => ({
            value: row.badge_id,
            label: `${row.badge_id} (${row.time})`,
        })),
        placeholder: "Choose badge",
        onChange: (value) => opts.onAnswer("badge_id", value),
    });
    renderMiniInput(wrap, {
        label: "Key time",
        value: opts.state.answers.time ?? "",
        placeholder: "17:58",
        onChange: (value) => opts.onAnswer("time", value),
    });
    renderMiniActions(wrap, {
        canSubmit: opts.projected?.gate_open ?? true,
        onSubmit: () => opts.onSubmit(source),
        onReset: opts.onReset,
    });
    renderMiniFeedback(wrap, opts.state);
}

function renderMg3Widget(
    panel: HTMLElement,
    opts: {
        isDemoProfile: boolean;
        source: { time: string; item: string; receiptId?: string } | null;
        state: MinigameUiState;
        projected: ProjectedMinigameState | undefined;
        learning: LearningProjection | null | undefined;
        onAnswer: (field: "time" | "item", value: string) => void;
        onSubmit: (source: { time: string; item: string; receiptId?: string }) => void;
        onReset: () => void;
    }
): void {
    const wrap = document.createElement("div");
    wrap.className = "notebook-minigame";
    panel.appendChild(wrap);

    const title = document.createElement("div");
    title.className = "notebook-minigame-title";
    title.textContent = "Receipt Check (MG3)";
    wrap.appendChild(title);

    if (!opts.source) {
        renderMiniInfo(wrap, "Read a receipt first (O9) to unlock this exercise.");
        return;
    }

    renderMiniSource(wrap, `Recu\nHeure: ${opts.source.time}\nArticle: ${opts.source.item}`);
    renderProjectedStatus(wrap, opts.projected, opts.state, opts.isDemoProfile);
    renderScaffoldingHints(wrap, opts.learning, "MG3_RECEIPT_READING", opts.isDemoProfile);
    renderMiniInput(wrap, {
        label: "Time",
        value: opts.state.answers.time ?? "",
        placeholder: "17:52",
        onChange: (value) => opts.onAnswer("time", value),
    });
    renderMiniInput(wrap, {
        label: "Item",
        value: opts.state.answers.item ?? "",
        placeholder: "cafe filtre",
        onChange: (value) => opts.onAnswer("item", value),
    });
    renderMiniActions(wrap, {
        canSubmit: opts.projected?.gate_open ?? true,
        onSubmit: () => opts.onSubmit(opts.source!),
        onReset: opts.onReset,
    });
    renderMiniFeedback(wrap, opts.state);
}

function renderMg4Widget(
    panel: HTMLElement,
    opts: {
        isDemoProfile: boolean;
        source: Mg4Source | null;
        state: MinigameUiState;
        projected: ProjectedMinigameState | undefined;
        learning: LearningProjection | null | undefined;
        onAnswer: (field: "slot1" | "slot2" | "slot3", value: string) => void;
        onSubmit: (source: Mg4Source) => void;
        onReset: () => void;
    }
): void {
    const wrap = document.createElement("div");
    wrap.className = "notebook-minigame";
    panel.appendChild(wrap);

    const title = document.createElement("div");
    title.className = "notebook-minigame-title";
    title.textContent = "Torn Note Rebuild (MG4)";
    wrap.appendChild(title);

    if (!opts.source) {
        renderMiniInfo(wrap, "Recover torn-note evidence first to unlock this exercise.");
        return;
    }
    const source = opts.source;

    renderMiniSource(wrap, `Note dechiree\n${source.prompt}\nOptions: ${source.options.join(", ")}`);
    renderProjectedStatus(wrap, opts.projected, opts.state, opts.isDemoProfile);
    renderScaffoldingHints(wrap, opts.learning, "MG4_TORN_NOTE_RECONSTRUCTION", opts.isDemoProfile);
    renderMiniSelect(wrap, {
        label: "Word 1",
        value: opts.state.answers.slot1 ?? "",
        options: source.options.map((option) => ({ value: option, label: option })),
        placeholder: "Choose word",
        onChange: (value) => opts.onAnswer("slot1", value),
    });
    renderMiniSelect(wrap, {
        label: "Word 2",
        value: opts.state.answers.slot2 ?? "",
        options: source.options.map((option) => ({ value: option, label: option })),
        placeholder: "Choose word",
        onChange: (value) => opts.onAnswer("slot2", value),
    });
    renderMiniSelect(wrap, {
        label: "Word 3",
        value: opts.state.answers.slot3 ?? "",
        options: source.options.map((option) => ({ value: option, label: option })),
        placeholder: "Choose word",
        onChange: (value) => opts.onAnswer("slot3", value),
    });
    renderMiniActions(wrap, {
        canSubmit: opts.projected?.gate_open ?? true,
        onSubmit: () => opts.onSubmit(source),
        onReset: opts.onReset,
    });
    renderMiniFeedback(wrap, opts.state);
}

function renderMiniSource(container: HTMLElement, text: string): void {
    const source = document.createElement("pre");
    source.className = "notebook-minigame-source";
    source.textContent = text;
    container.appendChild(source);
}

function renderMiniInfo(container: HTMLElement, text: string): void {
    const line = document.createElement("div");
    line.className = "notebook-minigame-info";
    line.textContent = text;
    container.appendChild(line);
}

function renderMiniInput(
    container: HTMLElement,
    opts: {
        label: string;
        value: string;
        placeholder: string;
        onChange: (value: string) => void;
    }
): void {
    const row = document.createElement("label");
    row.className = "notebook-minigame-input-row";
    const label = document.createElement("span");
    label.className = "notebook-minigame-label";
    label.textContent = opts.label;
    const input = document.createElement("input");
    input.className = "notebook-minigame-input";
    input.type = "text";
    input.value = opts.value;
    input.placeholder = opts.placeholder;
    input.addEventListener("input", () => opts.onChange(input.value));
    row.append(label, input);
    container.appendChild(row);
}

function renderMiniSelect(
    container: HTMLElement,
    opts: {
        label: string;
        value: string;
        options: Array<{ value: string; label: string }>;
        placeholder: string;
        onChange: (value: string) => void;
    }
): void {
    const row = document.createElement("label");
    row.className = "notebook-minigame-input-row";
    const label = document.createElement("span");
    label.className = "notebook-minigame-label";
    label.textContent = opts.label;
    const select = document.createElement("select");
    select.className = "notebook-minigame-input";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = opts.placeholder;
    select.appendChild(placeholder);
    for (const option of opts.options) {
        const node = document.createElement("option");
        node.value = option.value;
        node.textContent = option.label;
        select.appendChild(node);
    }
    select.value = opts.value;
    select.addEventListener("change", () => opts.onChange(select.value));
    row.append(label, select);
    container.appendChild(row);
}

function renderMiniActions(
    container: HTMLElement,
    opts: {
        canSubmit: boolean;
        onSubmit: () => void;
        onReset: () => void;
    }
): void {
    const row = document.createElement("div");
    row.className = "notebook-minigame-actions";
    const submit = document.createElement("button");
    submit.type = "button";
    submit.className = "notebook-minigame-btn";
    submit.textContent = "Submit";
    submit.disabled = !opts.canSubmit;
    submit.addEventListener("click", opts.onSubmit);
    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "notebook-minigame-btn";
    reset.textContent = "Reset";
    reset.addEventListener("click", opts.onReset);
    row.append(submit, reset);
    container.appendChild(row);
}

function renderMiniFeedback(container: HTMLElement, state: MinigameUiState): void {
    if (!state.feedback) return;
    const line = document.createElement("div");
    line.className = `notebook-minigame-feedback ${state.passed ? "is-pass" : "is-fail"}`;
    line.textContent = state.feedback;
    container.appendChild(line);
}

function renderProjectedStatus(
    container: HTMLElement,
    projected: ProjectedMinigameState | undefined,
    local: MinigameUiState,
    isDemoProfile: boolean
): void {
    const line = document.createElement("div");
    line.className = "notebook-minigame-status";
    if (isDemoProfile) {
        if (!projected) {
            line.textContent = "Status: waiting";
        } else {
            const gateState = projected.gate_open === false ? "blocked" : "ready";
            line.textContent = `Status: ${projected.status} (${gateState})`;
        }
    } else if (!projected) {
        line.textContent = `Local attempts: ${local.attempts}`;
    } else {
        const passRequired = projected.pass_score_required ?? projected.max_score;
        const gate = projected.gate_open === false ? ` | gate: ${projected.gate_code ?? "blocked"}` : "";
        line.textContent =
            `Projected status: ${projected.status} | projected attempts: ${projected.attempt_count} | ` +
            `score: ${projected.score}/${projected.max_score} (pass ${passRequired})${gate} | ` +
            `local attempts: ${local.attempts}`;
    }
    container.appendChild(line);
}

function renderScaffoldingHints(
    container: HTMLElement,
    learning: NonNullable<WorldState["dialogue"]>["learning"] | null | undefined,
    targetMinigameId: string,
    isDemoProfile: boolean
): void {
    if (isDemoProfile) return;
    if (!learning) return;
    const policy = learning.scaffolding_policy;
    if (policy.target_minigame_id && policy.target_minigame_id !== targetMinigameId) return;

    const hints: string[] = [];
    if (policy.soft_hint_key) hints.push(`Soft hint: ${policy.soft_hint_key}`);
    if (policy.sentence_stem_key) hints.push(`Sentence stem: ${policy.sentence_stem_key}`);
    if (policy.rephrase_set_id) hints.push(`Rephrase set: ${policy.rephrase_set_id}`);
    if (policy.english_meta_allowed && policy.english_meta_key) {
        hints.push(`EN meta-help: ${policy.english_meta_key}`);
    }
    hints.push(`Prompt: ${policy.prompt_generosity}`);
    hints.push(`Confirm: ${policy.confirmation_strength}`);
    if (hints.length === 0) return;

    const block = document.createElement("div");
    block.className = "notebook-minigame-hints";
    block.textContent = `Scaffolding (${policy.current_hint_level}): ${hints.join(" | ")}`;
    container.appendChild(block);
}

function evaluateMg1(
    state: MinigameUiState,
    source: { title: string; date: string },
    confirmationStrength: ConfirmationStrengthMode
): MinigameUiState {
    const titleOk = normalizeAnswer(state.answers.title ?? "") === normalizeAnswer(source.title);
    const dateOk = normalizeAnswer(state.answers.date ?? "") === normalizeAnswer(source.date);
    const passed = titleOk && dateOk;
    const score = (titleOk ? 1 : 0) + (dateOk ? 1 : 0);
    return {
        ...state,
        attempts: state.attempts + 1,
        passed,
        feedback:
            confirmationStrength === "compact"
                ? passed
                    ? "Correct."
                    : "Incorrect. Retry."
                : passed
                  ? `Correct (${score}/2).`
                  : `Incorrect (${score}/2). Check title/date and retry.`,
    };
}

function evaluateMg3(
    state: MinigameUiState,
    source: { time: string; item: string },
    confirmationStrength: ConfirmationStrengthMode
): MinigameUiState {
    const timeOk = normalizeAnswer(state.answers.time ?? "") === normalizeAnswer(source.time);
    const itemOk = normalizeAnswer(state.answers.item ?? "") === normalizeAnswer(source.item);
    const passed = timeOk && itemOk;
    const score = (timeOk ? 1 : 0) + (itemOk ? 1 : 0);
    return {
        ...state,
        attempts: state.attempts + 1,
        passed,
        feedback:
            confirmationStrength === "compact"
                ? passed
                    ? "Correct."
                    : "Incorrect. Retry."
                : passed
                  ? `Correct (${score}/2).`
                  : `Incorrect (${score}/2). Check time/item and retry.`,
    };
}

function evaluateMg2(
    state: MinigameUiState,
    source: Mg2Source,
    confirmationStrength: ConfirmationStrengthMode
): MinigameUiState {
    const important = source.entries.find((row) => normalizeAnswer(row.time) === "17:58") ?? source.entries[0];
    const badgeOk = normalizeAnswer(state.answers.badge_id ?? "") === normalizeAnswer(important?.badge_id ?? "");
    const timeOk = normalizeAnswer(state.answers.time ?? "") === normalizeAnswer("17:58");
    const passed = badgeOk && timeOk;
    const score = (badgeOk ? 1 : 0) + (timeOk ? 1 : 0);
    return {
        ...state,
        attempts: state.attempts + 1,
        passed,
        feedback:
            confirmationStrength === "compact"
                ? passed
                    ? "Correct."
                    : "Incorrect. Retry."
                : passed
                  ? `Correct (${score}/2).`
                  : `Incorrect (${score}/2). Find the 17:58 entry and retry.`,
    };
}

const MG4_EXPECTED_BY_VARIANT: Record<string, [string, string, string]> = {
    torn_note_a: ["chariot", "livraison", "17h58"],
    torn_note_b: ["pret", "badge", "dix-huit"],
    torn_note_c: ["vitrine", "entre-ouverte", "17h58"],
};

function evaluateMg4(
    state: MinigameUiState,
    source: Mg4Source,
    confirmationStrength: ConfirmationStrengthMode
): MinigameUiState {
    const expected = MG4_EXPECTED_BY_VARIANT[source.variantId] ?? ["", "", ""];
    const firstOk = normalizeAnswer(state.answers.slot1 ?? "") === normalizeAnswer(expected[0]);
    const secondOk = normalizeAnswer(state.answers.slot2 ?? "") === normalizeAnswer(expected[1]);
    const thirdOk = normalizeAnswer(state.answers.slot3 ?? "") === normalizeAnswer(expected[2]);
    const passed = firstOk && secondOk && thirdOk;
    const score = (firstOk ? 1 : 0) + (secondOk ? 1 : 0) + (thirdOk ? 1 : 0);
    return {
        ...state,
        attempts: state.attempts + 1,
        passed,
        feedback:
            confirmationStrength === "compact"
                ? passed
                    ? "Correct."
                    : "Incorrect. Retry."
                : passed
                  ? `Correct (${score}/3).`
                  : `Incorrect (${score}/3). Rebuild the torn-note sequence.`,
    };
}

function normalizeAnswer(value: string): string {
    return value.trim().toLowerCase().replace(/\s+/g, " ");
}

function renderKeyObjectLeads(
    panel: HTMLElement,
    investigation: KvpInvestigationState,
    isDemoProfile: boolean
): void {
    const guideById = new Map(listMbamObjectGuides().map((row) => [row.object_id, row]));
    const leadRows = [...investigation.objects]
        .filter((row) => row.affordances.length > 0)
        .sort((a, b) => {
            const guideA = guideById.get(a.object_id);
            const guideB = guideById.get(b.object_id);
            const priorityA = guideA?.starter_priority ?? 99;
            const priorityB = guideB?.starter_priority ?? 99;
            if (priorityA !== priorityB) return priorityA - priorityB;

            const aUnseen = a.affordances.length - a.observed_affordances.length;
            const bUnseen = b.affordances.length - b.observed_affordances.length;
            if (aUnseen !== bUnseen) return bUnseen - aUnseen;
            return a.object_id.localeCompare(b.object_id);
        });

    if (leadRows.length === 0) {
        renderInfo(panel, "No object leads are visible yet.");
        return;
    }

    const list = document.createElement("div");
    list.className = "notebook-list";
    panel.appendChild(list);

    for (const row of leadRows) {
        const guide = guideById.get(row.object_id) ?? getMbamObjectGuide(row.object_id);
        const title = guide?.label ?? labelForObject(row.object_id);
        const observedCount = row.observed_affordances.length;
        const totalCount = row.affordances.length;
        const nextAction = row.affordances.find((actionId) => !row.observed_affordances.includes(actionId)) ?? null;

        const line = document.createElement("div");
        line.className = "notebook-row";
        if (nextAction) line.classList.add("is-lead");
        line.textContent = isDemoProfile
            ? `${title}  ${observedCount}/${totalCount} leads checked`
            : `${title} (${row.object_id})  ${observedCount}/${totalCount} leads checked`;
        list.appendChild(line);

        const detail = document.createElement("div");
        detail.className = "notebook-mini";
        const locationHint = guide?.location_hint ?? "Location hint not available.";
        const nextHint = nextAction
            ? `Next: ${labelMbamAction(nextAction)}. ${hintMbamAction(nextAction)}`
            : "All listed actions reviewed.";
        const contradictionHint = guide?.contradiction_relevant
            ? "Useful for contradiction timeline checks."
            : "";
        detail.textContent = `${locationHint} | ${nextHint}${contradictionHint ? ` | ${contradictionHint}` : ""}`;
        panel.appendChild(detail);
    }
}

function renderEvidenceTray(panel: HTMLElement, investigation: KvpInvestigationState): void {
    const collected = new Set(investigation.evidence.collected_ids);
    const discovered = investigation.evidence.discovered_ids;
    if (discovered.length === 0 && investigation.evidence.observed_not_collected_ids.length === 0) {
        renderInfo(panel, "No evidence found yet.");
        return;
    }

    const list = document.createElement("div");
    list.className = "notebook-list";
    panel.appendChild(list);

    for (const evidenceId of discovered) {
        const row = document.createElement("div");
        row.className = "notebook-row";
        row.textContent = `${labelForEvidence(evidenceId)}  ${collected.has(evidenceId) ? "(collected)" : "(found)"}`;
        list.appendChild(row);
    }

    const observedOnly = investigation.evidence.observed_not_collected_ids.map(extractEvidenceIdFromObservedClue).filter(Boolean) as string[];
    for (const evidenceId of observedOnly) {
        if (collected.has(evidenceId)) continue;
        const row = document.createElement("div");
        row.className = "notebook-row is-observed";
        row.textContent = `${labelForEvidence(evidenceId)}  (seen, not collected)`;
        list.appendChild(row);
    }

    const relevantObjects = investigation.objects
        .filter((obj) => obj.observed_affordances.length > 0)
        .map((obj) => `${labelForObject(obj.object_id)} (${obj.observed_affordances.length} observed actions)`);
    if (relevantObjects.length > 0) {
        renderInfo(panel, `Relevant objects: ${relevantObjects.join(" | ")}`);
    }
}

function renderFactVisibility(panel: HTMLElement, investigation: KvpInvestigationState): void {
    const knownFacts = investigation.facts.known_fact_ids;
    if (knownFacts.length === 0) {
        renderInfo(panel, "No known facts yet.");
        return;
    }
    const list = document.createElement("div");
    list.className = "notebook-list";
    panel.appendChild(list);
    for (const factId of knownFacts) {
        const row = document.createElement("div");
        row.className = "notebook-row";
        row.textContent = `${factId}  ${labelForFact(factId)}`;
        list.appendChild(row);
    }
}

function renderContradictions(
    panel: HTMLElement,
    state: WorldState,
    investigation: KvpInvestigationState,
    isDemoProfile: boolean
): void {
    const contradictions = investigation.contradictions;
    const surfaced = new Set(state.dialogue?.surfaced_scene_ids ?? []);
    const contradictionScenes = ["S3", "S5"].filter((sceneId) => surfaced.has(sceneId));
    const actionRoute = contradictionScenes.length > 0
        ? `Conversations: present_evidence / challenge_contradiction in ${contradictionScenes.join(", ")}`
        : "Conversations: present evidence first; contradiction scenes appear as the case advances.";

    renderLines(panel, isDemoProfile
        ? [
            ["Accusation requirement", contradictions.required_for_accusation ? "required" : "not required"],
            ["Contradiction status", contradictions.requirement_satisfied ? "ready" : "building"],
            ["Where to use", actionRoute],
        ]
        : [
            ["Required for accusation", contradictions.required_for_accusation ? "yes" : "no"],
            ["Requirement satisfied", contradictions.requirement_satisfied ? "yes" : "no"],
            ["Unlockable edges", String(contradictions.unlockable_edge_ids.length)],
            ["Known edges", String(contradictions.known_edge_ids.length)],
            ["Where to use", actionRoute],
        ]);

    if (!isDemoProfile && contradictions.unlockable_edge_ids.length > 0) {
        const unlockable = document.createElement("div");
        unlockable.className = "notebook-mini";
        unlockable.textContent = `Unlockable: ${contradictions.unlockable_edge_ids.map(labelMbamContradictionEdge).join(", ")}`;
        panel.appendChild(unlockable);
    }
    if (!isDemoProfile && contradictions.known_edge_ids.length > 0) {
        const known = document.createElement("div");
        known.className = "notebook-mini";
        known.textContent = `Known: ${contradictions.known_edge_ids.map(labelMbamContradictionEdge).join(", ")}`;
        panel.appendChild(known);
    }
    if (!contradictions.requirement_satisfied && contradictions.unlockable_edge_ids.length > 0) {
        renderInfo(
            panel,
            "Potential contradiction leads found. Corroborate timeline clues, then challenge the contradiction in Conversations."
        );
    } else if (!contradictions.requirement_satisfied) {
        renderInfo(
            panel,
            "No contradiction link confirmed yet. Keep gathering timeline clues from objects and conversations."
        );
    } else {
        renderInfo(
            panel,
            "Contradiction path is ready. Final decisions are now better supported."
        );
    }
}

function renderTimeline(panel: HTMLElement, investigation: KvpInvestigationState): void {
    const knownFactSet = new Set(investigation.facts.known_fact_ids);
    const ordered = FACT_TIMELINE_ORDER.filter((factId) => knownFactSet.has(factId));
    if (ordered.length === 0) {
        renderInfo(panel, "No timeline clues yet.");
        return;
    }
    const list = document.createElement("div");
    list.className = "notebook-list";
    panel.appendChild(list);
    for (const factId of ordered) {
        const row = document.createElement("div");
        row.className = "notebook-row is-timeline";
        row.textContent = `${factId}  ${labelForFact(factId)}`;
        list.appendChild(row);
    }
    renderInfo(panel, "Timeline clues help you challenge contradictions and support final decisions.");
}

function renderSectionTitle(panel: HTMLElement, text: string): void {
    const title = document.createElement("div");
    title.className = "notebook-section-title";
    title.textContent = text;
    panel.appendChild(title);
}

function renderOnboardingSteps(
    panel: HTMLElement,
    steps: Array<{ label: string; done: boolean }>
): void {
    const list = document.createElement("div");
    list.className = "notebook-list";
    panel.appendChild(list);

    for (const step of steps) {
        const row = document.createElement("div");
        row.className = "notebook-row";
        row.textContent = `${step.done ? "[x]" : "[ ]"} ${step.label}`;
        list.appendChild(row);
    }
}

function renderLines(panel: HTMLElement, lines: Array<[string, string]>): void {
    for (const [labelText, valueText] of lines) {
        const row = document.createElement("div");
        row.className = "notebook-line";
        const label = document.createElement("span");
        label.className = "notebook-label";
        label.textContent = labelText;
        const value = document.createElement("span");
        value.className = "notebook-value";
        value.textContent = valueText;
        row.append(label, value);
        panel.appendChild(row);
    }
}

function renderInfo(panel: HTMLElement, text: string): void {
    const line = document.createElement("div");
    line.className = "notebook-info";
    line.textContent = text;
    panel.appendChild(line);
}

function extractEvidenceIdFromObservedClue(clueId: string): string | null {
    const parts = clueId.split(":");
    if (parts.length < 3) return null;
    const evidenceId = parts[2] ?? "";
    return evidenceId.length > 0 ? evidenceId : null;
}

function labelForEvidence(evidenceId: string): string {
    return EVIDENCE_LABELS[evidenceId] ?? evidenceId;
}

function labelForFact(factId: string): string {
    return FACT_LABELS[factId] ?? factId;
}

function labelForObject(objectId: string): string {
    return OBJECT_LABELS[objectId] ?? objectId;
}
