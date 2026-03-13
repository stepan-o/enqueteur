// src/ui/notebookPanel.ts
import type { KvpInvestigationState, WorldState, WorldStore } from "../state/worldStore";
import { createScopedTranslator, getSharedLocaleStore } from "../i18n";
import { resolvePresentationField, resolvePresentationFieldList } from "../app/presentationText";
import {
    buildMbamCaseSetupGuide,
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

const EVIDENCE_LABEL_KEYS: Record<string, string> = {
    E1_TORN_NOTE: "notebook.evidence_label.E1_TORN_NOTE",
    E2_CAFE_RECEIPT: "notebook.evidence_label.E2_CAFE_RECEIPT",
    E3_METHOD_TRACE: "notebook.evidence_label.E3_METHOD_TRACE",
};

const FACT_LABEL_KEYS: Record<string, string> = {
    N1: "notebook.fact_label.N1",
    N2: "notebook.fact_label.N2",
    N3: "notebook.fact_label.N3",
    N4: "notebook.fact_label.N4",
    N5: "notebook.fact_label.N5",
    N6: "notebook.fact_label.N6",
    N7: "notebook.fact_label.N7",
    N8: "notebook.fact_label.N8",
};

const FACT_TIMELINE_ORDER: string[] = ["N4", "N3", "N1", "N5", "N6", "N7", "N8", "N2"];

const OBJECT_LABEL_KEYS: Record<string, string> = {
    O1_DISPLAY_CASE: "notebook.object_label.O1_DISPLAY_CASE",
    O2_MEDALLION: "notebook.object_label.O2_MEDALLION",
    O3_WALL_LABEL: "notebook.object_label.O3_WALL_LABEL",
    O4_BENCH: "notebook.object_label.O4_BENCH",
    O5_VISITOR_LOGBOOK: "notebook.object_label.O5_VISITOR_LOGBOOK",
    O6_BADGE_TERMINAL: "notebook.object_label.O6_BADGE_TERMINAL",
    O7_SECURITY_BINDER: "notebook.object_label.O7_SECURITY_BINDER",
    O8_KEYPAD_DOOR: "notebook.object_label.O8_KEYPAD_DOOR",
    O9_RECEIPT_PRINTER: "notebook.object_label.O9_RECEIPT_PRINTER",
    O10_BULLETIN_BOARD: "notebook.object_label.O10_BULLETIN_BOARD",
};

const localeStore = getSharedLocaleStore();
const t = createScopedTranslator(() => localeStore.getLocale());

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
                summary: t("notebook.minigame.connection_not_ready"),
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
        title.textContent = t("notebook.title");
        panel.appendChild(title);

        const investigation = lastState.investigation;
        if (!investigation) {
            renderInfo(panel, t("notebook.loading"));
            return;
        }

        const onboarding = buildMbamOnboardingView(lastState);
        const setupGuide = buildMbamCaseSetupGuide(lastState);
        const playtestPath = buildMbamPlaytestPathView(lastState);
        const isDemoProfile = presentationProfile === "demo";
        renderSectionTitle(panel, t("notebook.section.case_brief"));
        renderInfo(panel, onboarding.caseSummary);
        renderSectionTitle(panel, t("notebook.section.case_setup"));
        renderInfo(panel, t("notebook.setup.what_happened", { incident: setupGuide.incident }));
        renderInfo(panel, t("notebook.setup.inspect_first", { inspect: setupGuide.firstInspect }));
        renderInfo(panel, t("notebook.setup.talk_first", { talk: setupGuide.firstTalkTo }));
        renderInfo(panel, t("notebook.setup.default_demo_route"));
        for (const step of setupGuide.progressionPath) {
            renderInfo(panel, `- ${step}`);
        }
        renderSectionTitle(panel, t("notebook.section.start_here"));
        renderOnboardingSteps(panel, onboarding.steps);
        renderInfo(panel, t("notebook.current_lead", { lead: onboarding.currentLead }));
        if (!isDemoProfile) {
            renderSectionTitle(panel, playtestPath.title);
            renderOnboardingSteps(panel, playtestPath.steps);
            renderInfo(panel, playtestPath.currentMilestone);
            renderLines(panel, [
                [t("notebook.line.case"), lastState.caseState?.case_id ?? "MBAM_01"],
                [t("notebook.line.seed"), lastState.caseState?.seed ?? "-"],
                [t("notebook.line.truth_epoch"), String(investigation.truth_epoch)],
            ]);
        } else {
            renderLines(panel, [[t("notebook.line.case"), onboarding.caseTitle]]);
        }

        renderSectionTitle(panel, t("notebook.section.key_object_leads"));
        renderKeyObjectLeads(panel, investigation, isDemoProfile);

        renderSectionTitle(panel, t("notebook.section.evidence_tray"));
        renderEvidenceTray(panel, investigation, isDemoProfile);

        renderSectionTitle(panel, t("notebook.section.known_facts"));
        renderFactVisibility(panel, investigation, isDemoProfile);

        renderSectionTitle(panel, t("notebook.section.contradictions"));
        renderContradictions(panel, lastState, investigation, isDemoProfile);

        renderSectionTitle(panel, t("notebook.section.timeline_clues"));
        renderTimeline(panel, investigation, isDemoProfile);

        renderSectionTitle(panel, t("notebook.section.field_exercises"));
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
                            summary: t("notebook.minigame.connection_not_ready"),
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
                    feedback: t("notebook.minigame.submitting"),
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
                            summary: t("notebook.minigame.connection_not_ready"),
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
                    feedback: t("notebook.minigame.submitting"),
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
                            summary: t("notebook.minigame.connection_not_ready"),
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
                    feedback: t("notebook.minigame.submitting"),
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
                            summary: t("notebook.minigame.connection_not_ready"),
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
                    feedback: t("notebook.minigame.submitting"),
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

    let localeReady = false;
    localeStore.subscribe(() => {
        if (!localeReady) {
            localeReady = true;
            return;
        }
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
        source: resolveMg1Source(labelKnownState),
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
    const prompt = resolvePresentationField(knownState, "torn_note_prompt");
    const variantId = knownState.torn_note_variant_id;
    const options = resolvePresentationFieldList(knownState, "torn_note_options", "torn_note_option_keys");
    if (typeof prompt !== "string" || typeof variantId !== "string" || !options) {
        return null;
    }
    if (options.length < 3) return null;
    return { variantId, prompt, options };
}

function resolveMg1Source(knownState: Record<string, unknown>): { title: string; date: string } | null {
    const title = resolvePresentationField(knownState, "title");
    const date = knownState.date;
    if (typeof date !== "string" || !title) return null;
    return { title, date };
}

function resolveMg3Source(knownState: Record<string, unknown>): {
    time: string;
    item: string;
    receiptId?: string;
} | null {
    const time = knownState.time;
    const item = resolvePresentationField(knownState, "item");
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
    title.textContent = t("notebook.mg1.title");
    wrap.appendChild(title);

    if (!opts.source) {
        renderMiniInfo(wrap, t("notebook.mg1.unlock_hint"));
        return;
    }

    renderMiniSource(wrap, t("notebook.mg1.source", { title: opts.source.title, date: opts.source.date }));
    renderProjectedStatus(wrap, opts.projected, opts.state, opts.isDemoProfile);
    renderScaffoldingHints(wrap, opts.learning, "MG1_LABEL_READING", opts.isDemoProfile);
    renderMiniInput(wrap, {
        label: t("notebook.mg1.field.title"),
        value: opts.state.answers.title ?? "",
        placeholder: t("notebook.mg1.placeholder.title"),
        onChange: (value) => opts.onAnswer("title", value),
    });
    renderMiniInput(wrap, {
        label: t("notebook.mg1.field.date"),
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
    title.textContent = t("notebook.mg2.title");
    wrap.appendChild(title);

    if (!opts.source) {
        renderMiniInfo(wrap, t("notebook.mg2.unlock_hint"));
        return;
    }
    const source = opts.source;

    renderMiniSource(
        wrap,
        t("notebook.mg2.source", {
            entries: source.entries.map((row) => `${row.badge_id} | ${row.time} | ${row.door}`).join("\n"),
        })
    );
    renderProjectedStatus(wrap, opts.projected, opts.state, opts.isDemoProfile);
    renderScaffoldingHints(wrap, opts.learning, "MG2_BADGE_LOG", opts.isDemoProfile);
    renderMiniSelect(wrap, {
        label: t("notebook.mg2.field.important_entry"),
        value: opts.state.answers.badge_id ?? "",
        options: source.entries.map((row) => ({
            value: row.badge_id,
            label: `${row.badge_id} (${row.time})`,
        })),
        placeholder: t("notebook.mg2.placeholder.badge"),
        onChange: (value) => opts.onAnswer("badge_id", value),
    });
    renderMiniInput(wrap, {
        label: t("notebook.mg2.field.key_time"),
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
    title.textContent = t("notebook.mg3.title");
    wrap.appendChild(title);

    if (!opts.source) {
        renderMiniInfo(wrap, t("notebook.mg3.unlock_hint"));
        return;
    }

    renderMiniSource(wrap, t("notebook.mg3.source", { time: opts.source.time, item: opts.source.item }));
    renderProjectedStatus(wrap, opts.projected, opts.state, opts.isDemoProfile);
    renderScaffoldingHints(wrap, opts.learning, "MG3_RECEIPT_READING", opts.isDemoProfile);
    renderMiniInput(wrap, {
        label: t("notebook.mg3.field.time"),
        value: opts.state.answers.time ?? "",
        placeholder: "17:52",
        onChange: (value) => opts.onAnswer("time", value),
    });
    renderMiniInput(wrap, {
        label: t("notebook.mg3.field.item"),
        value: opts.state.answers.item ?? "",
        placeholder: t("notebook.mg3.placeholder.item"),
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
    title.textContent = t("notebook.mg4.title");
    wrap.appendChild(title);

    if (!opts.source) {
        renderMiniInfo(wrap, t("notebook.mg4.unlock_hint"));
        return;
    }
    const source = opts.source;

    renderMiniSource(wrap, t("notebook.mg4.source", {
        prompt: source.prompt,
        options: source.options.join(", "),
    }));
    renderProjectedStatus(wrap, opts.projected, opts.state, opts.isDemoProfile);
    renderScaffoldingHints(wrap, opts.learning, "MG4_TORN_NOTE_RECONSTRUCTION", opts.isDemoProfile);
    renderMiniSelect(wrap, {
        label: t("notebook.mg4.field.word_1"),
        value: opts.state.answers.slot1 ?? "",
        options: source.options.map((option) => ({ value: option, label: option })),
        placeholder: t("notebook.mg4.placeholder.word"),
        onChange: (value) => opts.onAnswer("slot1", value),
    });
    renderMiniSelect(wrap, {
        label: t("notebook.mg4.field.word_2"),
        value: opts.state.answers.slot2 ?? "",
        options: source.options.map((option) => ({ value: option, label: option })),
        placeholder: t("notebook.mg4.placeholder.word"),
        onChange: (value) => opts.onAnswer("slot2", value),
    });
    renderMiniSelect(wrap, {
        label: t("notebook.mg4.field.word_3"),
        value: opts.state.answers.slot3 ?? "",
        options: source.options.map((option) => ({ value: option, label: option })),
        placeholder: t("notebook.mg4.placeholder.word"),
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
    submit.textContent = t("notebook.mini_action.submit");
    submit.disabled = !opts.canSubmit;
    submit.addEventListener("click", opts.onSubmit);
    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "notebook-minigame-btn";
    reset.textContent = t("notebook.mini_action.reset");
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
            line.textContent = t("notebook.status.waiting_projection");
        } else {
            if (projected.gate_open === false) {
                line.textContent = t("notebook.status.blocked_prereqs");
            } else if (projected.status === "completed") {
                line.textContent = t("notebook.status.completed");
            } else if (projected.status === "passed") {
                line.textContent = t("notebook.status.passed");
            } else {
                line.textContent = t("notebook.status.available");
            }
        }
    } else if (!projected) {
        line.textContent = t("notebook.status.local_attempts", { attempts: local.attempts });
    } else {
        const passRequired = projected.pass_score_required ?? projected.max_score;
        const gate = projected.gate_open === false
            ? ` | ${t("notebook.status.gate")}: ${projected.gate_code ?? t("notebook.status.blocked_short")}`
            : "";
        line.textContent =
            `${t("notebook.status.projected_status")}: ${projected.status} | ` +
            `${t("notebook.status.projected_attempts")}: ${projected.attempt_count} | ` +
            `${t("notebook.status.score")}: ${projected.score}/${projected.max_score} (${t("notebook.status.pass")} ${passRequired})${gate} | ` +
            `${t("notebook.status.local_attempts_label")}: ${local.attempts}`;
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
    if (policy.soft_hint_key) hints.push(t("notebook.hints.soft_hint", { value: policy.soft_hint_key }));
    if (policy.sentence_stem_key) hints.push(t("notebook.hints.sentence_stem", { value: policy.sentence_stem_key }));
    if (policy.rephrase_set_id) hints.push(t("notebook.hints.rephrase_set", { value: policy.rephrase_set_id }));
    if (policy.english_meta_allowed && policy.english_meta_key) {
        hints.push(t("notebook.hints.en_meta_help", { value: policy.english_meta_key }));
    }
    hints.push(t("notebook.hints.prompt", { value: policy.prompt_generosity }));
    hints.push(t("notebook.hints.confirm", { value: policy.confirmation_strength }));
    if (hints.length === 0) return;

    const block = document.createElement("div");
    block.className = "notebook-minigame-hints";
    block.textContent = t("notebook.hints.block", {
        level: policy.current_hint_level,
        hints: hints.join(" | "),
    });
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
                    ? t("notebook.feedback.correct_short")
                    : t("notebook.feedback.incorrect_retry")
                : passed
                  ? t("notebook.feedback.correct_score", { score, max: 2 })
                  : t("notebook.feedback.mg1_retry", { score }),
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
                    ? t("notebook.feedback.correct_short")
                    : t("notebook.feedback.incorrect_retry")
                : passed
                  ? t("notebook.feedback.correct_score", { score, max: 2 })
                  : t("notebook.feedback.mg3_retry", { score }),
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
                    ? t("notebook.feedback.correct_short")
                    : t("notebook.feedback.incorrect_retry")
                : passed
                  ? t("notebook.feedback.correct_score", { score, max: 2 })
                  : t("notebook.feedback.mg2_retry", { score }),
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
                    ? t("notebook.feedback.correct_short")
                    : t("notebook.feedback.incorrect_retry")
                : passed
                  ? t("notebook.feedback.correct_score", { score, max: 3 })
                  : t("notebook.feedback.mg4_retry", { score }),
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
        renderInfo(panel, t("notebook.object_leads.none"));
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
            ? t("notebook.object_leads.row_demo", { title, observedCount, totalCount })
            : t("notebook.object_leads.row", { title, objectId: row.object_id, observedCount, totalCount });
        list.appendChild(line);

        const detail = document.createElement("div");
        detail.className = "notebook-mini";
        const locationHint = guide?.location_hint ?? t("notebook.object_leads.location_missing");
        const nextHint = nextAction
            ? t("notebook.object_leads.next_hint", { action: labelMbamAction(nextAction), hint: hintMbamAction(nextAction) })
            : t("notebook.object_leads.all_reviewed");
        const contradictionHint = guide?.contradiction_relevant
            ? t("notebook.object_leads.contradiction_relevant")
            : "";
        detail.textContent = `${locationHint} | ${nextHint}${contradictionHint ? ` | ${contradictionHint}` : ""}`;
        panel.appendChild(detail);
    }
}

function renderEvidenceTray(panel: HTMLElement, investigation: KvpInvestigationState, isDemoProfile: boolean): void {
    const collected = new Set(investigation.evidence.collected_ids);
    const discovered = investigation.evidence.discovered_ids;
    if (discovered.length === 0 && investigation.evidence.observed_not_collected_ids.length === 0) {
        renderInfo(panel, t("notebook.evidence.none"));
        return;
    }

    const list = document.createElement("div");
    list.className = "notebook-list";
    panel.appendChild(list);

    for (const evidenceId of discovered) {
        const row = document.createElement("div");
        row.className = "notebook-row";
        row.textContent = `${labelForEvidence(evidenceId, !isDemoProfile)}  ${
            collected.has(evidenceId) ? t("notebook.evidence.collected") : t("notebook.evidence.found")
        }`;
        list.appendChild(row);
    }

    const observedOnly = investigation.evidence.observed_not_collected_ids.map(extractEvidenceIdFromObservedClue).filter(Boolean) as string[];
    for (const evidenceId of observedOnly) {
        if (collected.has(evidenceId)) continue;
        const row = document.createElement("div");
        row.className = "notebook-row is-observed";
        row.textContent = `${labelForEvidence(evidenceId, !isDemoProfile)}  ${t("notebook.evidence.seen_not_collected")}`;
        list.appendChild(row);
    }

    const relevantObjects = investigation.objects
        .filter((obj) => obj.observed_affordances.length > 0)
        .map((obj) => t("notebook.evidence.object_observed_actions", {
            object: labelForObject(obj.object_id),
            count: obj.observed_affordances.length,
        }));
    if (relevantObjects.length > 0) {
        renderInfo(panel, t("notebook.evidence.relevant_objects", { objects: relevantObjects.join(" | ") }));
    }
}

function renderFactVisibility(panel: HTMLElement, investigation: KvpInvestigationState, isDemoProfile: boolean): void {
    const knownFacts = investigation.facts.known_fact_ids;
    if (knownFacts.length === 0) {
        renderInfo(panel, t("notebook.facts.none"));
        return;
    }
    const list = document.createElement("div");
    list.className = "notebook-list";
    panel.appendChild(list);
    for (const factId of knownFacts) {
        const row = document.createElement("div");
        row.className = "notebook-row";
        row.textContent = isDemoProfile
            ? labelForFact(factId, false)
            : `${factId}  ${labelForFact(factId, true)}`;
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
    const contradictionSceneLabels = contradictionScenes.map(labelScene);
    const actionRoute = contradictionScenes.length > 0
        ? t("notebook.contradictions.route_with_scenes", { scenes: contradictionSceneLabels.join(", ") })
        : t("notebook.contradictions.route_default");

    renderLines(panel, isDemoProfile
        ? [
            [t("notebook.contradictions.demo.accusation_requirement"), contradictions.required_for_accusation ? t("notebook.value.required") : t("notebook.value.not_required")],
            [t("notebook.contradictions.demo.status"), contradictions.requirement_satisfied ? t("notebook.value.ready") : t("notebook.value.building")],
            [t("notebook.contradictions.demo.where_to_use"), actionRoute],
        ]
        : [
            [t("notebook.contradictions.required_for_accusation"), contradictions.required_for_accusation ? t("notebook.value.yes") : t("notebook.value.no")],
            [t("notebook.contradictions.requirement_satisfied"), contradictions.requirement_satisfied ? t("notebook.value.yes") : t("notebook.value.no")],
            [t("notebook.contradictions.unlockable_edges"), String(contradictions.unlockable_edge_ids.length)],
            [t("notebook.contradictions.known_edges"), String(contradictions.known_edge_ids.length)],
            [t("notebook.contradictions.where_to_use"), actionRoute],
        ]);

    if (!isDemoProfile && contradictions.unlockable_edge_ids.length > 0) {
        const unlockable = document.createElement("div");
        unlockable.className = "notebook-mini";
        unlockable.textContent = t("notebook.contradictions.unlockable", {
            edges: contradictions.unlockable_edge_ids.map(labelMbamContradictionEdge).join(", "),
        });
        panel.appendChild(unlockable);
    }
    if (!isDemoProfile && contradictions.known_edge_ids.length > 0) {
        const known = document.createElement("div");
        known.className = "notebook-mini";
        known.textContent = t("notebook.contradictions.known", {
            edges: contradictions.known_edge_ids.map(labelMbamContradictionEdge).join(", "),
        });
        panel.appendChild(known);
    }
    if (!contradictions.requirement_satisfied && contradictions.unlockable_edge_ids.length > 0) {
        renderInfo(
            panel,
            t("notebook.contradictions.potential_leads")
        );
    } else if (!contradictions.requirement_satisfied) {
        renderInfo(
            panel,
            t("notebook.contradictions.none_confirmed")
        );
    } else {
        renderInfo(
            panel,
            t("notebook.contradictions.ready")
        );
    }
}

function renderTimeline(panel: HTMLElement, investigation: KvpInvestigationState, isDemoProfile: boolean): void {
    const knownFactSet = new Set(investigation.facts.known_fact_ids);
    const ordered = FACT_TIMELINE_ORDER.filter((factId) => knownFactSet.has(factId));
    if (ordered.length === 0) {
        renderInfo(panel, t("notebook.timeline.none"));
        return;
    }
    const list = document.createElement("div");
    list.className = "notebook-list";
    panel.appendChild(list);
    for (const factId of ordered) {
        const row = document.createElement("div");
        row.className = "notebook-row is-timeline";
        row.textContent = isDemoProfile
            ? labelForFact(factId, false)
            : `${factId}  ${labelForFact(factId, true)}`;
        list.appendChild(row);
    }
    renderInfo(panel, t("notebook.timeline.help"));
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

function labelForEvidence(evidenceId: string, includeCode = true): string {
    const label = EVIDENCE_LABEL_KEYS[evidenceId] ? t(EVIDENCE_LABEL_KEYS[evidenceId]) : evidenceId;
    return includeCode ? label : stripLeadingCode(label);
}

function labelForFact(factId: string, includeCode = true): string {
    const label = FACT_LABEL_KEYS[factId] ? t(FACT_LABEL_KEYS[factId]) : factId;
    return includeCode ? label : stripLeadingCode(label);
}

function labelForObject(objectId: string): string {
    const key = OBJECT_LABEL_KEYS[objectId];
    return key ? t(key) : objectId;
}

function labelScene(sceneId: string): string {
    const labels: Record<string, string> = {
        S1: "notebook.scene.S1",
        S2: "notebook.scene.S2",
        S3: "notebook.scene.S3",
        S4: "notebook.scene.S4",
        S5: "notebook.scene.S5",
    };
    const key = labels[sceneId];
    return key ? t(key) : sceneId;
}

function stripLeadingCode(value: string): string {
    return value.replace(/^[A-Z]\d+\s+/, "");
}
