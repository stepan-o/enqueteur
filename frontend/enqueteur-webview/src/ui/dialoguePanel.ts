// src/ui/dialoguePanel.ts
import type { KvpDialogueTurnLog, KvpNpcSemanticState, WorldState, WorldStore } from "../state/worldStore";
import { createScopedTranslator, getSharedLocaleStore } from "../i18n";
import { buildMbamCaseSetupGuide, buildMbamOnboardingView, labelMbamContradictionEdge } from "./mbamOnboarding";

export type DialogueTurnSlotValue = {
    slot_name: string;
    value: string;
};

export type DialogueTurnSubmitRequest = {
    sceneId: string;
    npcId: string;
    intentId: string;
    providedSlots: DialogueTurnSlotValue[];
    presentedFactIds: string[];
    presentedEvidenceIds: string[];
    utteranceText?: string;
    tick: number;
};

export type DialogueTurnSubmitResult = {
    status: "submitted" | "accepted" | "blocked" | "repair" | "refused" | "invalid" | "unavailable" | "error";
    code: string;
    summary?: string;
    revealed_fact_ids?: string[];
};

export type DialogueTurnDispatcher = (
    request: DialogueTurnSubmitRequest
) => Promise<DialogueTurnSubmitResult> | DialogueTurnSubmitResult;

export type DialoguePanelOpts = {
    dispatchDialogueTurn?: DialogueTurnDispatcher;
    canDispatchDialogueTurn?: () => boolean;
    presentationProfile?: "demo" | "playtest" | "dev";
};

export type DialogueInspectSelection =
    | { kind: "room"; id: number }
    | { kind: "agent"; id: number }
    | { kind: "object"; id: number }
    | null;

export type DialoguePanelHandle = {
    root: HTMLElement;
    setInspectSelection: (selection: DialogueInspectSelection) => void;
    setPresentationProfile?: (profile: "demo" | "playtest" | "dev") => void;
};

type SceneConfig = {
    allowedIntents: string[];
    requiredSceneSlots: string[];
    primaryNpcDefault: string;
};

const SCENE_CONFIG: Record<string, SceneConfig> = {
    S1: {
        allowedIntents: [
            "ask_what_happened",
            "ask_when",
            "ask_where",
            "ask_who",
            "request_permission",
            "summarize_understanding",
            "reassure",
            "goodbye",
        ],
        requiredSceneSlots: [],
        primaryNpcDefault: "elodie",
    },
    S2: {
        allowedIntents: [
            "ask_what_seen",
            "ask_when",
            "request_access",
            "request_permission",
            "present_evidence",
            "summarize_understanding",
            "reassure",
            "goodbye",
        ],
        requiredSceneSlots: ["reason"],
        primaryNpcDefault: "marc",
    },
    S3: {
        allowedIntents: [
            "ask_when",
            "ask_where",
            "ask_who",
            "ask_what_seen",
            "present_evidence",
            "challenge_contradiction",
            "summarize_understanding",
            "reassure",
            "goodbye",
        ],
        requiredSceneSlots: ["time"],
        primaryNpcDefault: "samira",
    },
    S4: {
        allowedIntents: [
            "ask_what_seen",
            "ask_when",
            "ask_where",
            "ask_who",
            "present_evidence",
            "summarize_understanding",
            "reassure",
            "goodbye",
        ],
        requiredSceneSlots: ["time"],
        primaryNpcDefault: "jo",
    },
    S5: {
        allowedIntents: [
            "present_evidence",
            "challenge_contradiction",
            "summarize_understanding",
            "accuse",
            "request_permission",
            "reassure",
            "goodbye",
        ],
        requiredSceneSlots: ["person", "reason"],
        primaryNpcDefault: "elodie",
    },
};

const INTENT_REQUIRED_SLOTS: Record<string, string[]> = {
    present_evidence: ["item"],
    accuse: ["person", "reason"],
};
const INTENT_LABEL_KEYS: Record<string, string> = {
    ask_what_happened: "dialogue.intent.ask_what_happened",
    ask_when: "dialogue.intent.ask_when",
    ask_where: "dialogue.intent.ask_where",
    ask_who: "dialogue.intent.ask_who",
    ask_what_seen: "dialogue.intent.ask_what_seen",
    request_permission: "dialogue.intent.request_permission",
    request_access: "dialogue.intent.request_access",
    present_evidence: "dialogue.intent.present_evidence",
    challenge_contradiction: "dialogue.intent.challenge_contradiction",
    summarize_understanding: "dialogue.intent.summarize_understanding",
    reassure: "dialogue.intent.reassure",
    accuse: "dialogue.intent.accuse",
    goodbye: "dialogue.intent.goodbye",
};

const NPC_LABEL_KEYS: Record<string, string> = {
    elodie: "dialogue.npc.elodie",
    marc: "dialogue.npc.marc",
    samira: "dialogue.npc.samira",
    jo: "dialogue.npc.jo",
    laurent: "dialogue.npc.laurent",
    outsider: "dialogue.npc.outsider",
};

const SCENE_LABEL_KEYS: Record<string, string> = {
    S1: "notebook.scene.S1",
    S2: "notebook.scene.S2",
    S3: "notebook.scene.S3",
    S4: "notebook.scene.S4",
    S5: "notebook.scene.S5",
};

const WORLD_ROOM_ID_TO_TOKEN: Record<number, string> = {
    1: "MBAM_LOBBY",
    2: "GALLERY_AFFICHES",
    3: "SECURITY_OFFICE",
    4: "SERVICE_CORRIDOR",
    5: "CAFE_DE_LA_RUE",
};

type LearningState = NonNullable<NonNullable<WorldState["dialogue"]>["learning"]>;
type LearningSceneSummaryState = LearningState["summary_by_scene"][number];
type HintLevel = "soft_hint" | "sentence_stem" | "rephrase_choice" | "english_meta_help";

const HINT_LEVEL_ORDER: HintLevel[] = ["soft_hint", "sentence_stem", "rephrase_choice", "english_meta_help"];

const HINT_LEVEL_LABEL_KEYS: Record<HintLevel, string> = {
    soft_hint: "dialogue.hint_level.soft_hint",
    sentence_stem: "dialogue.hint_level.sentence_stem",
    rephrase_choice: "dialogue.hint_level.rephrase_choice",
    english_meta_help: "dialogue.hint_level.english_meta_help",
};

const SOFT_HINT_KEYS: Record<string, string> = {
    "hint:s1_incident_scope": "dialogue.soft_hint.s1_incident_scope",
    "hint:s2_security_protocol": "dialogue.soft_hint.s2_security_protocol",
    "hint:s3_timeline_anchor": "dialogue.soft_hint.s3_timeline_anchor",
    "hint:s4_cafe_witness_window": "dialogue.soft_hint.s4_cafe_witness_window",
    "hint:s5_corroboration_requirements": "dialogue.soft_hint.s5_corroboration_requirements",
};

const SENTENCE_STEM_KEYS: Record<string, string> = {
    "stem:s1_polite_incident": "dialogue.sentence_stem.s1_polite_incident",
    "stem:s2_access_request": "dialogue.sentence_stem.s2_access_request",
    "stem:s3_time_sequence": "dialogue.sentence_stem.s3_time_sequence",
    "stem:s4_witness_prompt": "dialogue.sentence_stem.s4_witness_prompt",
    "stem:s5_confrontation_structure": "dialogue.sentence_stem.s5_confrontation_structure",
};

const REPHRASE_CHOICE_KEYS: Record<string, string[]> = {
    "rephrase:s1_incident_core": [
        "dialogue.rephrase.s1_incident_core.1",
        "dialogue.rephrase.s1_incident_core.2",
        "dialogue.rephrase.s1_incident_core.3",
    ],
    "rephrase:s2_access_reason": [
        "dialogue.rephrase.s2_access_reason.1",
        "dialogue.rephrase.s2_access_reason.2",
        "dialogue.rephrase.s2_access_reason.3",
    ],
    "rephrase:s3_timeline_checks": [
        "dialogue.rephrase.s3_timeline_checks.1",
        "dialogue.rephrase.s3_timeline_checks.2",
        "dialogue.rephrase.s3_timeline_checks.3",
    ],
    "rephrase:s4_clothing_timestamp": [
        "dialogue.rephrase.s4_clothing_timestamp.1",
        "dialogue.rephrase.s4_clothing_timestamp.2",
        "dialogue.rephrase.s4_clothing_timestamp.3",
    ],
    "rephrase:s5_accusation_logic": [
        "dialogue.rephrase.s5_accusation_logic.1",
        "dialogue.rephrase.s5_accusation_logic.2",
        "dialogue.rephrase.s5_accusation_logic.3",
    ],
};

const EN_META_HELP_KEYS: Record<string, string> = {
    "meta:s1_english_prompting": "dialogue.en_meta.s1_english_prompting",
    "meta:s2_english_polite_security": "dialogue.en_meta.s2_english_polite_security",
    "meta:s3_english_timeline_frame": "dialogue.en_meta.s3_english_timeline_frame",
    "meta:s4_english_witness_focus": "dialogue.en_meta.s4_english_witness_focus",
    "meta:s5_english_reasoning_frame": "dialogue.en_meta.s5_english_reasoning_frame",
};

const SUMMARY_CODE_KEYS: Record<string, string> = {
    summary_passed: "dialogue.summary_code.summary_passed",
    summary_required: "dialogue.summary_code.summary_required",
    summary_needed: "dialogue.summary_code.summary_needed",
    summary_insufficient_facts: "dialogue.summary_code.summary_insufficient_facts",
    summary_missing_key_fact: "dialogue.summary_code.summary_missing_key_fact",
};

const localeStore = getSharedLocaleStore();
const t = createScopedTranslator(() => localeStore.getLocale());

type SubmitFeedback = {
    tick: number;
    sceneId: string;
    intentId: string;
    result: DialogueTurnSubmitResult;
};

export function mountDialoguePanel(store: WorldStore, opts: DialoguePanelOpts = {}): DialoguePanelHandle {
    const root = document.createElement("div");
    root.className = "dialogue-root";

    const panel = document.createElement("div");
    panel.className = "dialogue-panel";
    root.appendChild(panel);

    let lastState: WorldState | null = null;
    let selectedIntent: string | null = null;
    let slotValues: Record<string, string> = {};
    let factInput = "";
    let evidenceInput = "";
    let utteranceInput = "";
    let pending = false;
    let submitFeedback: SubmitFeedback | null = null;
    let inspectSelection: DialogueInspectSelection = null;
    let presentationProfile: "demo" | "playtest" | "dev" = opts.presentationProfile ?? "playtest";

    const render = (): void => {
        panel.innerHTML = "";
        if (!lastState || !lastState.dialogue) {
            panel.style.display = "none";
            return;
        }
        panel.style.display = "block";
        const dialogue = lastState.dialogue;
        const onboarding = buildMbamOnboardingView(lastState);
        const setupGuide = buildMbamCaseSetupGuide(lastState);
        const detailed = presentationProfile !== "demo";

        const title = document.createElement("div");
        title.className = "dialogue-title";
        title.textContent = t("dialogue.title");
        panel.appendChild(title);

        const focusSceneId = pickFocusSceneId(dialogue);
        const focusNpcId = resolveSceneNpcId(lastState, dialogue.recent_turns, focusSceneId);
        const npcCardState = resolveRelevantNpcState(lastState, inspectSelection, focusNpcId);
        const sceneConfig = focusSceneId ? SCENE_CONFIG[focusSceneId] : null;
        let requiredSlots: string[] = [];

        if (sceneConfig) {
            const allowedIntents = sceneConfig.allowedIntents;
            if (!selectedIntent || !allowedIntents.includes(selectedIntent)) {
                selectedIntent = allowedIntents[0] ?? null;
            }
            requiredSlots = collectRequiredSlots(sceneConfig, selectedIntent);
            slotValues = syncSlotValues(slotValues, requiredSlots);
        }

        renderSectionTitle(panel, t("dialogue.section.character_read"));
        renderNpcStateCard(panel, npcCardState, detailed);
        const completedSetupSteps = onboarding.steps.filter((step) => step.done).length;
        const needsStarterGuidance = completedSetupSteps < 2 || dialogue.recent_turns.length === 0;
        if (needsStarterGuidance) {
            renderSectionTitle(panel, t("dialogue.section.case_setup_hint"));
            renderInfo(panel, t("dialogue.setup.what_happened", { incident: setupGuide.incident }));
            renderInfo(panel, t("dialogue.setup.inspect_first", { inspect: setupGuide.firstInspect }));
            renderInfo(panel, t("dialogue.setup.talk_first", { talk: setupGuide.firstTalkTo }));
        }

        renderDataLines(panel, detailed
            ? [
                [t("dialogue.line.active_scene"), dialogue.active_scene_id ?? t("dialogue.value.none")],
                [t("dialogue.line.focus_scene"), focusSceneId ?? t("dialogue.value.none")],
                [t("dialogue.line.current_npc"), npcCardState?.npc_id ?? focusNpcId ?? t("dialogue.value.unknown")],
                [t("dialogue.line.known_dialogue_facts"), String(dialogue.revealed_fact_ids.length)],
                [
                    t("dialogue.line.contradiction_path"),
                    dialogue.contradiction_requirement_satisfied ? t("dialogue.value.satisfied") : t("dialogue.value.pending"),
                ],
            ]
            : [
                [t("dialogue.line.current_scene"), labelScene(dialogue.active_scene_id)],
                [t("dialogue.line.who_to_question"), labelNpc(npcCardState?.npc_id ?? focusNpcId)],
                [t("dialogue.line.dialogue_facts"), String(dialogue.revealed_fact_ids.length)],
            ]);
        if (detailed) {
            renderLearningSlice(panel, dialogue);
        }

        renderSectionTitle(panel, t("dialogue.section.scene_progress"));
        renderSceneProgress(
            panel,
            dialogue.scene_completion,
            dialogue.surfaced_scene_ids,
            focusSceneId,
            !detailed
        );

        if (detailed) {
            renderSectionTitle(panel, t("dialogue.section.summary_guidance"));
            renderSummaryHintSection(panel, {
                dialogue,
                focusSceneId,
                selectedIntent,
                requiredSlots,
            });
        }
        renderSectionTitle(panel, t("dialogue.section.contradiction_clues"));
        renderContradictionRoute(panel, lastState, focusSceneId, selectedIntent, detailed);

        renderSectionTitle(panel, t("dialogue.section.choose_line"));
        if (!focusSceneId || !sceneConfig || !focusNpcId) {
            renderInfo(panel, t("dialogue.info.no_active_scene"));
        } else {
            if (dialogue.recent_turns.length === 0) {
                renderInfo(
                    panel,
                    t("dialogue.info.start_simple", { npc: labelNpc(focusNpcId) })
                );
            }
            const allowedIntents = sceneConfig.allowedIntents;

            renderIntentButtons(panel, {
                intents: allowedIntents,
                selectedIntent,
                friendlyLabels: presentationProfile === "demo",
                onSelect: (intentId) => {
                    selectedIntent = intentId;
                    slotValues = syncSlotValues(slotValues, collectRequiredSlots(sceneConfig, selectedIntent));
                    render();
                },
            });

            renderSlotInputs(panel, {
                requiredSlots,
                values: slotValues,
                friendlyLabels: presentationProfile === "demo",
                onChange: (slotName, value) => {
                    slotValues[slotName] = value;
                },
            });

            if (detailed) {
                renderAuxInputs(panel, {
                    factInput,
                    evidenceInput,
                    utteranceInput,
                    onFactChange: (value) => {
                        factInput = value;
                    },
                    onEvidenceChange: (value) => {
                        evidenceInput = value;
                    },
                    onUtteranceChange: (value) => {
                        utteranceInput = value;
                    },
                });
                renderReferenceInputsHint(panel, lastState);
            } else {
                renderInfo(panel, t("dialogue.info.pick_intent"));
            }

            const minFacts = dialogue.summary_rules.current_scene_min_fact_count;
            const summaryRequired = dialogue.summary_rules.required_scene_ids.includes(focusSceneId);
            if (summaryRequired) {
                renderInfo(
                    panel,
                    t("dialogue.info.summary_required_here", { count: minFacts ?? 1 })
                );
            }
            if (detailed && (selectedIntent === "present_evidence" || selectedIntent === "challenge_contradiction")) {
                renderContradictionIntentHint(panel, lastState, selectedIntent);
            }

            const dispatchAvailable = opts.canDispatchDialogueTurn
                ? opts.canDispatchDialogueTurn()
                : Boolean(opts.dispatchDialogueTurn);
            const canSubmit = dispatchAvailable && !pending && selectedIntent !== null;
            const submitBtn = document.createElement("button");
            submitBtn.type = "button";
            submitBtn.className = "dialogue-submit";
            submitBtn.disabled = !canSubmit;
            submitBtn.textContent = pending ? t("dialogue.action.sending") : t("dialogue.action.submit_line");
            submitBtn.addEventListener("click", () => {
                if (!selectedIntent) return;
                const currentTick = lastState?.tick ?? 0;
                const request: DialogueTurnSubmitRequest = {
                    sceneId: focusSceneId,
                    npcId: focusNpcId,
                    intentId: selectedIntent,
                    providedSlots: requiredSlots
                        .map((slotName) => ({
                            slot_name: slotName,
                            value: (slotValues[slotName] ?? "").trim(),
                        }))
                        .filter((row) => row.value.length > 0),
                    presentedFactIds: parseCsvList(factInput),
                    presentedEvidenceIds: parseCsvList(evidenceInput),
                    utteranceText: utteranceInput.trim() || undefined,
                    tick: currentTick,
                };
                pending = true;
                render();
                void submitTurn(opts.dispatchDialogueTurn, request)
                    .then((result) => {
                        submitFeedback = {
                            tick: request.tick,
                            sceneId: request.sceneId,
                            intentId: request.intentId,
                            result,
                        };
                    })
                    .catch((err: unknown) => {
                        submitFeedback = {
                            tick: request.tick,
                            sceneId: request.sceneId,
                            intentId: request.intentId,
                            result: {
                                status: "error",
                                code: "dispatch_error",
                                summary: err instanceof Error ? err.message : String(err),
                            },
                        };
                    })
                    .finally(() => {
                        pending = false;
                        render();
                    });
            });
            panel.appendChild(submitBtn);

            if (!dispatchAvailable) {
                renderInfo(panel, t("dialogue.info.sending_unavailable_mode"));
            }
        }

        if (submitFeedback) {
            renderSectionTitle(panel, t("dialogue.section.latest_attempt"));
            renderDataLines(panel, [
                [t("dialogue.line.tick"), String(submitFeedback.tick)],
                [t("dialogue.line.scene"), detailed ? submitFeedback.sceneId : labelScene(submitFeedback.sceneId)],
                [t("dialogue.line.intent"), presentationProfile === "demo" ? labelIntent(submitFeedback.intentId) : submitFeedback.intentId],
                [
                    t("dialogue.line.status"),
                    detailed ? `${submitFeedback.result.status}/${submitFeedback.result.code}` : submitFeedback.result.status,
                ],
                [t("dialogue.line.summary"), submitFeedback.result.summary ?? t("dialogue.value.none")],
            ]);
        }

        renderSectionTitle(panel, t("dialogue.section.recent_turns"));
        renderTranscript(panel, dialogue.recent_turns, detailed);
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
        setInspectSelection: (selection) => {
            inspectSelection = selection;
            render();
        },
        setPresentationProfile: (profile) => {
            presentationProfile = profile;
            render();
        },
    };
}

async function submitTurn(
    dispatch: DialogueTurnDispatcher | undefined,
    request: DialogueTurnSubmitRequest
): Promise<DialogueTurnSubmitResult> {
    if (!dispatch) {
        return {
            status: "unavailable",
            code: "dispatch_unavailable",
            summary: t("dialogue.info.sending_not_configured"),
        };
    }
    return dispatch(request);
}

function pickFocusSceneId(dialogue: WorldState["dialogue"]): string | null {
    if (!dialogue) return null;
    if (dialogue.active_scene_id) return dialogue.active_scene_id;
    const byId = new Map(dialogue.scene_completion.map((row) => [row.scene_id, row.completion_state]));
    for (const sceneId of dialogue.surfaced_scene_ids) {
        if ((byId.get(sceneId) ?? "locked") === "in_progress") return sceneId;
    }
    for (const sceneId of dialogue.surfaced_scene_ids) {
        if ((byId.get(sceneId) ?? "locked") === "available") return sceneId;
    }
    return dialogue.surfaced_scene_ids[0] ?? null;
}

function resolveSceneNpcId(
    state: WorldState,
    transcript: KvpDialogueTurnLog[],
    sceneId: string | null
): string | null {
    if (!sceneId) return null;
    for (let i = transcript.length - 1; i >= 0; i -= 1) {
        const row = transcript[i];
        if (row.scene_id === sceneId && row.npc_id) return row.npc_id;
    }
    for (const row of state.npcSemantic) {
        if (row.current_scene_id === sceneId) return row.npc_id;
    }
    return SCENE_CONFIG[sceneId]?.primaryNpcDefault ?? null;
}

function resolveRelevantNpcState(
    state: WorldState,
    selection: DialogueInspectSelection,
    fallbackNpcId: string | null
): KvpNpcSemanticState | null {
    const fromSelection = resolveNpcFromSelection(state, selection, fallbackNpcId);
    if (fromSelection) return fromSelection;

    if (fallbackNpcId) {
        const fromFallback = state.npcSemantic.find((row) => row.npc_id === fallbackNpcId) ?? null;
        if (fromFallback) return fromFallback;
    }

    return [...state.npcSemantic].sort((a, b) => a.npc_id.localeCompare(b.npc_id))[0] ?? null;
}

function resolveNpcFromSelection(
    state: WorldState,
    selection: DialogueInspectSelection,
    preferredNpcId: string | null
): KvpNpcSemanticState | null {
    if (!selection) return null;
    const roomToken = roomTokenFromSelection(state, selection);
    if (!roomToken) return null;
    const candidates = state.npcSemantic.filter((row) => row.current_room_id === roomToken);
    if (candidates.length === 0) return null;
    if (preferredNpcId) {
        const preferred = candidates.find((row) => row.npc_id === preferredNpcId);
        if (preferred) return preferred;
    }
    return [...candidates].sort((a, b) => a.npc_id.localeCompare(b.npc_id))[0] ?? null;
}

function roomTokenFromSelection(state: WorldState, selection: Exclude<DialogueInspectSelection, null>): string | null {
    if (selection.kind === "room") {
        return WORLD_ROOM_ID_TO_TOKEN[selection.id] ?? null;
    }
    if (selection.kind === "object") {
        const roomId = state.objects.get(selection.id)?.room_id;
        return typeof roomId === "number" ? (WORLD_ROOM_ID_TO_TOKEN[roomId] ?? null) : null;
    }
    const roomId = state.agents.get(selection.id)?.room_id;
    return typeof roomId === "number" ? (WORLD_ROOM_ID_TO_TOKEN[roomId] ?? null) : null;
}

function renderNpcStateCard(panel: HTMLElement, npc: KvpNpcSemanticState | null, detailed: boolean): void {
    if (!npc) {
        renderInfo(panel, t("dialogue.info.no_character_focus"));
        return;
    }
    const card = document.createElement("div");
    card.className = "dialogue-npc-card";

    const portraitSlot = document.createElement("div");
    portraitSlot.className = "dialogue-npc-portrait";
    portraitSlot.textContent = detailed
        ? `${npc.npc_id}\n${npc.card_state.portrait_variant}`
        : labelNpc(npc.npc_id);

    const meta = document.createElement("div");
    meta.className = "dialogue-npc-meta";
    appendNpcLine(meta, t("dialogue.npc_line.emotion"), npc.emotion);
    appendNpcLine(meta, t("dialogue.npc_line.stance"), npc.stance);
    if (detailed) {
        appendNpcLine(meta, t("dialogue.npc_line.alignment"), npc.soft_alignment_hint);
        appendNpcLine(meta, t("dialogue.npc_line.trust_trend"), npc.card_state.trust_trend);
        appendNpcLine(meta, t("dialogue.npc_line.tell_cue"), npc.card_state.tell_cue ?? t("dialogue.value.none"));
        appendNpcLine(meta, t("dialogue.npc_line.suggested_mode"), npc.card_state.suggested_interaction_mode);
        appendNpcLine(meta, t("dialogue.npc_line.availability"), npc.availability);
    } else {
        appendNpcLine(meta, t("dialogue.npc_line.trust_trend"), npc.card_state.trust_trend);
        appendNpcLine(meta, t("dialogue.npc_line.availability"), npc.availability);
    }

    card.append(portraitSlot, meta);
    panel.appendChild(card);
}

function renderLearningSlice(panel: HTMLElement, dialogue: NonNullable<WorldState["dialogue"]>): void {
    const learning = dialogue.learning;
    if (!learning) return;
    renderSectionTitle(panel, t("dialogue.section.conversation_support"));
    renderDataLines(panel, [
        [t("dialogue.line.difficulty"), learning.difficulty_profile],
        [t("dialogue.line.hint_level"), learning.current_hint_level],
        [t("dialogue.line.suggested_style"), learning.scaffolding_policy.recommended_mode],
        [t("dialogue.line.french_required"), learning.scaffolding_policy.french_action_required ? t("dialogue.value.yes") : t("dialogue.value.no")],
        [t("dialogue.line.english_help"), learning.scaffolding_policy.english_meta_allowed ? t("dialogue.value.allowed") : t("dialogue.value.off")],
        [t("dialogue.line.prompt_level"), learning.scaffolding_policy.prompt_generosity],
        [t("dialogue.line.feedback_style"), learning.scaffolding_policy.confirmation_strength],
        [t("dialogue.line.summary_strictness"), learning.scaffolding_policy.summary_strictness],
        [t("dialogue.line.language_support"), learning.scaffolding_policy.language_support_level],
        [t("dialogue.line.support_profile"), learning.scaffolding_policy.reason_code],
    ]);
    const completedMgs = learning.minigames.filter((row) => row.completed).length;
    renderInfo(
        panel,
        t("dialogue.info.minigames_progress", {
            completed: completedMgs,
            total: learning.minigames.length,
            target: learning.scaffolding_policy.target_minigame_id ?? t("dialogue.value.none"),
        })
    );
}

function renderSummaryHintSection(
    panel: HTMLElement,
    opts: {
        dialogue: NonNullable<WorldState["dialogue"]>;
        focusSceneId: string | null;
        selectedIntent: string | null;
        requiredSlots: string[];
    }
): void {
    const learning = opts.dialogue.learning;
    if (!learning) {
        renderInfo(panel, t("dialogue.info.summary_guidance_unavailable"));
        return;
    }
    if (!opts.focusSceneId) {
        renderInfo(panel, t("dialogue.info.no_scene_for_summary"));
        return;
    }

    const summaryState = learning.summary_by_scene.find((row) => row.scene_id === opts.focusSceneId) ?? null;
    if (!summaryState) {
        renderInfo(panel, t("dialogue.info.no_summary_for_scene"));
        return;
    }

    renderSummaryPrompt(panel, opts.dialogue, summaryState, opts.focusSceneId, opts.selectedIntent, opts.requiredSlots);
    renderHintLadder(panel, learning, opts.focusSceneId, opts.requiredSlots);
}

function renderSummaryPrompt(
    panel: HTMLElement,
    dialogue: NonNullable<WorldState["dialogue"]>,
    summaryState: LearningSceneSummaryState,
    sceneId: string,
    selectedIntent: string | null,
    requiredSlots: string[]
): void {
    const block = document.createElement("div");
    block.className = "dialogue-summary-block";
    panel.appendChild(block);

    const requiredLabel = summaryState.required
        ? t("dialogue.summary.required_yes", { count: summaryState.effective_min_fact_count })
        : t("dialogue.value.no");
    renderDataLines(block, [
        [t("dialogue.line.scene"), sceneId],
        [t("dialogue.line.summary_state"), summaryState.status],
        [t("dialogue.line.summary_required"), requiredLabel],
        [t("dialogue.line.strictness"), summaryState.strictness_mode],
        [t("dialogue.line.attempts"), String(summaryState.attempt_count)],
    ]);

    const prompt = buildSummaryPrompt(sceneId, summaryState, selectedIntent, requiredSlots);
    const promptLine = document.createElement("div");
    promptLine.className = "dialogue-summary-prompt";
    promptLine.textContent = t("dialogue.summary.prompt_line", { prompt });
    block.appendChild(promptLine);

    const feedback = resolveSummaryFeedback(summaryState, dialogue.recent_turns, sceneId);
    if (feedback) {
        const feedbackLine = document.createElement("div");
        feedbackLine.className = "dialogue-summary-feedback";
        feedbackLine.textContent = t("dialogue.summary.feedback_line", { feedback });
        block.appendChild(feedbackLine);
    }
}

function renderHintLadder(
    panel: HTMLElement,
    learning: LearningState,
    sceneId: string,
    requiredSlots: string[]
): void {
    const ladder = document.createElement("div");
    ladder.className = "dialogue-hint-ladder";
    panel.appendChild(ladder);

    const title = document.createElement("div");
    title.className = "dialogue-hint-ladder-title";
    title.textContent = t("dialogue.hint_track.title", {
        level: learning.current_hint_level,
        profile: learning.difficulty_profile,
    });
    ladder.appendChild(title);

    const policy = learning.scaffolding_policy;
    if (policy.scene_id && policy.scene_id !== sceneId) {
        renderInfo(ladder, t("dialogue.hint_track.scene_tuned", { scene: policy.scene_id }));
    }

    const allowed = new Set(policy.allowed_hint_levels);
    for (const level of HINT_LEVEL_ORDER) {
        const row = document.createElement("div");
        row.className = "dialogue-hint-step";
        const isCurrent = level === policy.current_hint_level;
        const isAllowed = allowed.has(level);
        row.classList.add(isCurrent ? "is-current" : isAllowed ? "is-available" : "is-locked");

        const head = document.createElement("div");
        head.className = "dialogue-hint-head";
        head.textContent = `${t(HINT_LEVEL_LABEL_KEYS[level])} - ${
            isCurrent ? t("dialogue.hint_state.current") : isAllowed ? t("dialogue.hint_state.available") : t("dialogue.hint_state.locked")
        }`;
        row.appendChild(head);

        const body = document.createElement("div");
        body.className = "dialogue-hint-body";
        body.textContent = resolveHintBody(level, policy, sceneId, requiredSlots, isAllowed);
        row.appendChild(body);

        ladder.appendChild(row);
    }
}

function renderContradictionRoute(
    panel: HTMLElement,
    state: WorldState,
    focusSceneId: string | null,
    selectedIntent: string | null,
    detailed: boolean
): void {
    const investigation = state.investigation;
    const dialogue = state.dialogue;
    if (!investigation || !dialogue) {
        renderInfo(panel, t("dialogue.info.contradiction_clues_unavailable"));
        return;
    }

    const contradictions = investigation.contradictions;
    const surfaced = new Set(dialogue.surfaced_scene_ids);
    const usableScenes = dialogue.scene_completion
        .map((row) => row.scene_id)
        .filter((sceneId) => surfaced.has(sceneId) && sceneSupportsContradictionIntent(sceneId));
    const useScenesLabel = usableScenes.length > 0
        ? usableScenes.map((sceneId) => (detailed ? sceneId : labelScene(sceneId))).join(", ")
        : (detailed ? t("dialogue.value.none_surfaced_yet") : t("dialogue.value.none_available_yet"));
    const contradictionStatus = contradictions.requirement_satisfied
        ? t("dialogue.value.ready")
        : contradictions.unlockable_edge_ids.length > 0
          ? t("dialogue.value.lead_found")
          : t("dialogue.value.building");

    renderDataLines(panel, detailed
        ? [
            [t("dialogue.line.status"), contradictionStatus],
            [t("dialogue.line.required_for_accusation"), contradictions.required_for_accusation ? t("dialogue.value.yes") : t("dialogue.value.no")],
            [t("dialogue.line.use_in_scenes"), useScenesLabel],
            [t("dialogue.line.potential_links"), String(contradictions.unlockable_edge_ids.length)],
            [t("dialogue.line.known_links"), String(contradictions.known_edge_ids.length)],
        ]
        : [
            [t("dialogue.line.status"), contradictionStatus],
            [t("dialogue.line.where_to_use"), useScenesLabel],
        ]);
    if (detailed && contradictions.unlockable_edge_ids.length > 0) {
        renderInfo(
            panel,
            t("dialogue.info.potential_edges", {
                edges: contradictions.unlockable_edge_ids.map(labelMbamContradictionEdge).join(", "),
            })
        );
    }
    if (detailed && contradictions.known_edge_ids.length > 0) {
        renderInfo(
            panel,
            t("dialogue.info.known_edges", {
                edges: contradictions.known_edge_ids.map(labelMbamContradictionEdge).join(", "),
            })
        );
    }

    if (contradictions.requirement_satisfied) {
        renderInfo(panel, t("dialogue.info.contradiction_path_ready"));
    } else if (contradictions.unlockable_edge_ids.length > 0) {
        renderInfo(panel, t("dialogue.info.contradiction_leads_found"));
    } else {
        renderInfo(panel, t("dialogue.info.no_contradiction_lead"));
    }
    if (focusSceneId && !sceneSupportsContradictionIntent(focusSceneId)) {
        renderInfo(
            panel,
            detailed
                ? t("dialogue.info.scene_no_contradiction_detailed", { scene: focusSceneId })
                : t("dialogue.info.scene_no_contradiction")
        );
    }
    if (selectedIntent === "challenge_contradiction" && !contradictions.requirement_satisfied) {
        renderInfo(panel, t("dialogue.info.challenge_may_block"));
    }
}

function sceneSupportsContradictionIntent(sceneId: string): boolean {
    const config = SCENE_CONFIG[sceneId];
    if (!config) return false;
    return config.allowedIntents.includes("challenge_contradiction");
}

function buildSummaryPrompt(
    sceneId: string,
    summaryState: LearningSceneSummaryState,
    selectedIntent: string | null,
    requiredSlots: string[]
): string {
    const slotsLabel = requiredSlots.length > 0
        ? t("dialogue.summary.include_slots", { slots: requiredSlots.join(", ") })
        : t("dialogue.summary.no_mandatory_slots");
    const keyFactHint =
        summaryState.required_key_fact_count > 0
            ? t("dialogue.summary.include_key_fact")
            : t("dialogue.summary.use_unlocked_facts");
    const intentLabel = selectedIntent
        ? t("dialogue.summary.intent_context", { intent: selectedIntent })
        : t("dialogue.summary.intent_context_none");
    return t("dialogue.summary.prompt", { scene: sceneId, slots: slotsLabel, intent: intentLabel, facts: keyFactHint });
}

function resolveSummaryFeedback(
    summaryState: LearningSceneSummaryState,
    turns: KvpDialogueTurnLog[],
    sceneId: string
): string | null {
    const lastTurnCode = (() => {
        for (let i = turns.length - 1; i >= 0; i -= 1) {
            const row = turns[i];
            if (row.scene_id === sceneId && row.summary_check_code) return row.summary_check_code;
        }
        return null;
    })();
    const code = lastTurnCode ?? summaryState.last_summary_code;
    if (!code) return summaryState.status === "passed" ? t("dialogue.summary_code.summary_passed") : null;
    return SUMMARY_CODE_KEYS[code] ? t(SUMMARY_CODE_KEYS[code]) : t("dialogue.summary_code.unknown", { code });
}

function resolveHintBody(
    level: HintLevel,
    policy: LearningState["scaffolding_policy"],
    sceneId: string,
    requiredSlots: string[],
    isAllowed: boolean
): string {
    if (!isAllowed) {
        if (level === "english_meta_help" && !policy.english_meta_allowed) {
            return t("dialogue.hint.not_available_difficulty");
        }
        return t("dialogue.hint.locked");
    }

    if (level === "soft_hint") {
        const key = SOFT_HINT_KEYS[policy.soft_hint_key ?? ""];
        return key ? t(key) : t("dialogue.hint.soft_hint_fallback", { scene: sceneId });
    }
    if (level === "sentence_stem") {
        const key = SENTENCE_STEM_KEYS[policy.sentence_stem_key ?? ""];
        const base = key ? t(key) : t("dialogue.sentence_stem.fallback");
        if (requiredSlots.length === 0) return base;
        return t("dialogue.hint.sentence_stem_with_slots", { base, slots: requiredSlots.join(", ") });
    }
    if (level === "rephrase_choice") {
        const optionKeys = REPHRASE_CHOICE_KEYS[policy.rephrase_set_id ?? ""];
        if (!optionKeys || optionKeys.length === 0) return t("dialogue.hint.rephrase_fallback");
        return t("dialogue.hint.choose_one", { options: optionKeys.map((key) => t(key)).join(" / ") });
    }
    if (!policy.english_meta_allowed) {
        return t("dialogue.hint.english_unavailable");
    }
    const key = EN_META_HELP_KEYS[policy.english_meta_key ?? ""];
    return key ? t(key) : t("dialogue.hint.english_fallback");
}

function appendNpcLine(parent: HTMLElement, labelText: string, valueText: string): void {
    const row = document.createElement("div");
    row.className = "dialogue-npc-line";
    const label = document.createElement("span");
    label.className = "dialogue-npc-label";
    label.textContent = labelText;
    const value = document.createElement("span");
    value.className = "dialogue-npc-value";
    value.textContent = valueText;
    row.append(label, value);
    parent.appendChild(row);
}

function collectRequiredSlots(scene: SceneConfig, intentId: string | null): string[] {
    const out = new Set<string>(scene.requiredSceneSlots);
    if (intentId && INTENT_REQUIRED_SLOTS[intentId]) {
        for (const slot of INTENT_REQUIRED_SLOTS[intentId]) out.add(slot);
    }
    return Array.from(out.values());
}

function syncSlotValues(current: Record<string, string>, requiredSlots: string[]): Record<string, string> {
    const next: Record<string, string> = {};
    for (const slotName of requiredSlots) next[slotName] = current[slotName] ?? "";
    return next;
}

function parseCsvList(value: string): string[] {
    return value
        .split(",")
        .map((row) => row.trim())
        .filter((row) => row.length > 0);
}

function renderSceneProgress(
    panel: HTMLElement,
    rows: Array<{ scene_id: string; completion_state: string }>,
    surfacedSceneIds: string[],
    focusSceneId: string | null,
    friendlyLabels = false
): void {
    const wrap = document.createElement("div");
    wrap.className = "dialogue-scene-list";
    panel.appendChild(wrap);

    const surfaced = new Set(surfacedSceneIds);
    for (const row of rows) {
        const item = document.createElement("div");
        item.className = "dialogue-scene-row";
        if (row.scene_id === focusSceneId) item.classList.add("is-focus");
        const sceneLabel = friendlyLabels ? labelScene(row.scene_id) : row.scene_id;
        item.textContent = t("dialogue.scene_progress.row", {
            scene: sceneLabel,
            state: row.completion_state,
            surfaced: surfaced.has(row.scene_id) ? t("dialogue.scene_progress.surfaced") : "",
        }).trim();
        wrap.appendChild(item);
    }
}

function renderIntentButtons(
    panel: HTMLElement,
    opts: {
        intents: string[];
        selectedIntent: string | null;
        friendlyLabels?: boolean;
        onSelect: (intentId: string) => void;
    }
): void {
    const wrap = document.createElement("div");
    wrap.className = "dialogue-intents";
    panel.appendChild(wrap);
    for (const intentId of opts.intents) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "dialogue-intent-btn";
        if (opts.selectedIntent === intentId) btn.classList.add("is-active");
        btn.textContent = opts.friendlyLabels ? labelIntent(intentId) : intentId;
        btn.addEventListener("click", () => opts.onSelect(intentId));
        wrap.appendChild(btn);
    }
}

function renderSlotInputs(
    panel: HTMLElement,
    opts: {
        requiredSlots: string[];
        values: Record<string, string>;
        friendlyLabels?: boolean;
        onChange: (slotName: string, value: string) => void;
    }
): void {
    if (opts.requiredSlots.length === 0) {
        renderInfo(panel, t("dialogue.info.no_required_details"));
        return;
    }
    for (const slotName of opts.requiredSlots) {
        const row = document.createElement("label");
        row.className = "dialogue-input-row";
        const label = document.createElement("span");
        label.className = "dialogue-input-label";
        label.textContent = opts.friendlyLabels
            ? t("dialogue.slot.required", { slot: humanizeToken(slotName) })
            : t("dialogue.slot.raw", { slot: slotName });
        const input = document.createElement("input");
        input.className = "dialogue-input";
        input.type = "text";
        input.value = opts.values[slotName] ?? "";
        input.placeholder = t("dialogue.slot.placeholder", { slot: humanizeToken(slotName).toLowerCase() });
        input.addEventListener("input", () => {
            opts.onChange(slotName, input.value);
        });
        row.append(label, input);
        panel.appendChild(row);
    }
}

function renderAuxInputs(
    panel: HTMLElement,
    opts: {
        factInput: string;
        evidenceInput: string;
        utteranceInput: string;
        onFactChange: (value: string) => void;
        onEvidenceChange: (value: string) => void;
        onUtteranceChange: (value: string) => void;
    }
): void {
    const facts = renderAuxInput(
        t("dialogue.aux.facts_label"),
        opts.factInput,
        t("dialogue.aux.facts_placeholder"),
        opts.onFactChange
    );
    const evidence = renderAuxInput(
        t("dialogue.aux.evidence_label"),
        opts.evidenceInput,
        t("dialogue.aux.evidence_placeholder"),
        opts.onEvidenceChange
    );
    const utterance = renderAuxInput(
        t("dialogue.aux.utterance_label"),
        opts.utteranceInput,
        t("dialogue.aux.utterance_placeholder"),
        opts.onUtteranceChange
    );
    panel.append(facts, evidence, utterance);
}

function renderReferenceInputsHint(panel: HTMLElement, state: WorldState): void {
    const knownFacts = state.investigation?.facts.known_fact_ids ?? [];
    const knownEvidence = state.investigation?.evidence.discovered_ids ?? [];
    const factsLabel = knownFacts.length > 0 ? knownFacts.join(", ") : t("dialogue.value.none_yet");
    const evidenceLabel = knownEvidence.length > 0 ? knownEvidence.join(", ") : t("dialogue.value.none_yet");
    renderInfo(panel, t("dialogue.info.facts_you_can_cite", { facts: factsLabel }));
    renderInfo(panel, t("dialogue.info.evidence_you_can_cite", { evidence: evidenceLabel }));
}

function renderContradictionIntentHint(
    panel: HTMLElement,
    state: WorldState,
    selectedIntent: string
): void {
    const contradictions = state.investigation?.contradictions;
    if (!contradictions) return;
    if (selectedIntent === "present_evidence") {
        renderInfo(panel, t("dialogue.info.present_evidence_hint"));
        return;
    }
    if (contradictions.requirement_satisfied) {
        renderInfo(panel, t("dialogue.info.challenge_ready_hint"));
        return;
    }
    renderInfo(panel, t("dialogue.info.challenge_rejected_hint"));
}

function renderAuxInput(
    labelText: string,
    value: string,
    placeholder: string,
    onChange: (value: string) => void
): HTMLElement {
    const row = document.createElement("label");
    row.className = "dialogue-input-row";
    const label = document.createElement("span");
    label.className = "dialogue-input-label";
    label.textContent = labelText;
    const input = document.createElement("input");
    input.className = "dialogue-input";
    input.type = "text";
    input.value = value;
    input.placeholder = placeholder;
    input.addEventListener("input", () => onChange(input.value));
    row.append(label, input);
    return row;
}

function renderTranscript(panel: HTMLElement, turns: KvpDialogueTurnLog[], detailed: boolean): void {
    if (turns.length === 0) {
        renderInfo(panel, t("dialogue.info.no_turns"));
        return;
    }
    const list = document.createElement("div");
    list.className = "dialogue-transcript-list";
    panel.appendChild(list);
    for (let i = turns.length - 1; i >= 0; i -= 1) {
        const turn = turns[i];
        const row = document.createElement("div");
        row.className = `dialogue-turn dialogue-status-${turn.status}`;
        const line1 = document.createElement("div");
        line1.className = "dialogue-turn-main";
        line1.textContent = detailed
            ? `#${turn.turn_index} ${turn.scene_id} ${turn.npc_id} ${turn.intent_id}`
            : `#${turn.turn_index} ${labelScene(turn.scene_id)} ${labelIntent(turn.intent_id)}`;
        const line2 = document.createElement("div");
        line2.className = "dialogue-turn-meta";
        line2.textContent = detailed
            ? `${turn.status}/${turn.code}  mode:${turn.response_mode}`
            : `${turn.status}`;
        row.append(line1, line2);

        if (turn.npc_utterance_text) {
            const speech = document.createElement("div");
            speech.className = "dialogue-turn-detail";
            speech.textContent = t("dialogue.turn.npc_line", { line: turn.npc_utterance_text });
            row.appendChild(speech);
        }

        if (detailed && (turn.revealed_fact_ids.length > 0 || turn.summary_check_code || turn.repair_response_mode)) {
            const detail = document.createElement("div");
            detail.className = "dialogue-turn-detail";
            detail.textContent =
                `facts:[${turn.revealed_fact_ids.join(", ")}]` +
                (turn.summary_check_code ? ` summary:${turn.summary_check_code}` : "") +
                (turn.repair_response_mode ? ` repair:${turn.repair_response_mode}` : "");
            row.appendChild(detail);
        }
        if (detailed && (turn.short_rephrase_line || turn.summary_prompt_line || turn.hint_line)) {
            const guidance = document.createElement("div");
            guidance.className = "dialogue-turn-detail";
            guidance.textContent =
                (turn.short_rephrase_line ? `rephrase:${turn.short_rephrase_line}` : "") +
                (turn.summary_prompt_line ? ` summary_prompt:${turn.summary_prompt_line}` : "") +
                (turn.hint_line ? ` hint:${turn.hint_line}` : "");
            row.appendChild(guidance);
        }
        if (detailed && (turn.presentation_source || turn.presentation_reason_code)) {
            const source = document.createElement("div");
            source.className = "dialogue-turn-detail";
            source.textContent =
                `presentation:${turn.presentation_source ?? t("dialogue.value.na")}` +
                (turn.presentation_reason_code ? ` reason:${turn.presentation_reason_code}` : "");
            row.appendChild(source);
        }
        if (detailed && turn.presentation_metadata && turn.presentation_metadata.length > 0) {
            const meta = document.createElement("div");
            meta.className = "dialogue-turn-detail";
            meta.textContent = `presentation_meta:[${turn.presentation_metadata.join(", ")}]`;
            row.appendChild(meta);
        }
        list.appendChild(row);
    }
}

function renderSectionTitle(panel: HTMLElement, text: string): void {
    const title = document.createElement("div");
    title.className = "dialogue-section-title";
    title.textContent = text;
    panel.appendChild(title);
}

function renderDataLines(panel: HTMLElement, lines: Array<[string, string]>): void {
    for (const [labelText, valueText] of lines) {
        const row = document.createElement("div");
        row.className = "dialogue-line";
        const label = document.createElement("span");
        label.className = "dialogue-label";
        label.textContent = labelText;
        const value = document.createElement("span");
        value.className = "dialogue-value";
        value.textContent = valueText;
        row.append(label, value);
        panel.appendChild(row);
    }
}

function renderInfo(panel: HTMLElement, text: string): void {
    const line = document.createElement("div");
    line.className = "dialogue-info";
    line.textContent = text;
    panel.appendChild(line);
}

function labelNpc(npcId: string | null | undefined): string {
    if (!npcId) return t("dialogue.value.unknown");
    const key = NPC_LABEL_KEYS[npcId];
    return key ? t(key) : humanizeToken(npcId);
}

function labelScene(sceneId: string | null | undefined): string {
    if (!sceneId) return t("dialogue.value.not_selected");
    const key = SCENE_LABEL_KEYS[sceneId];
    return key ? t(key) : sceneId;
}

function labelIntent(intentId: string): string {
    const key = INTENT_LABEL_KEYS[intentId];
    return key ? t(key) : intentId;
}

function humanizeToken(value: string): string {
    const normalized = value.replace(/_/g, " ").trim();
    if (!normalized) return value;
    return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}
