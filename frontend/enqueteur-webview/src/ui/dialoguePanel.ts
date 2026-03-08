// src/ui/dialoguePanel.ts
import type { KvpDialogueTurnLog, KvpNpcSemanticState, WorldState, WorldStore } from "../state/worldStore";

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
};

export type DialogueInspectSelection =
    | { kind: "room"; id: number }
    | { kind: "agent"; id: number }
    | { kind: "object"; id: number }
    | null;

export type DialoguePanelHandle = {
    root: HTMLElement;
    setInspectSelection: (selection: DialogueInspectSelection) => void;
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

const HINT_LEVEL_LABELS: Record<HintLevel, string> = {
    soft_hint: "Soft Hint",
    sentence_stem: "Sentence Stem",
    rephrase_choice: "Rephrase Choices",
    english_meta_help: "English Meta-Help",
};

const SOFT_HINT_COPY: Record<string, string> = {
    "hint:s1_incident_scope": "Focus first on what is missing, where it was, and when the absence was noticed.",
    "hint:s2_security_protocol": "With Marc, a respectful reason unlocks process details better than pressure.",
    "hint:s3_timeline_anchor": "Use one concrete time anchor before asking where people moved.",
    "hint:s4_cafe_witness_window": "Jo remembers clothing and vibe first. Ask for time, then appearance.",
    "hint:s5_corroboration_requirements": "In confrontation, connect method + time + place with corroborated facts.",
};

const SENTENCE_STEM_COPY: Record<string, string> = {
    "stem:s1_polite_incident": "Je résume: l'objet manquant est ___, observé absent vers ___.",
    "stem:s2_access_request": "Je demande l'accès au journal des badges pour vérifier ___.",
    "stem:s3_time_sequence": "À ___, la personne ___ était dans ___.",
    "stem:s4_witness_prompt": "Vers ___, vous avez vu ___ près du café.",
    "stem:s5_confrontation_structure": "Je conclus: ___ a utilisé ___, puis dépôt à ___.",
};

const REPHRASE_CHOICES_COPY: Record<string, string[]> = {
    "rephrase:s1_incident_core": [
        "Que s'est-il passé exactement dans la galerie?",
        "À quelle heure avez-vous constaté la disparition?",
        "Pouvez-vous confirmer l'objet manquant?",
    ],
    "rephrase:s2_access_reason": [
        "J'ai besoin du journal pour vérifier la chronologie.",
        "Je respecte la procédure, puis-je consulter l'entrée clé?",
        "Pouvez-vous autoriser un accès limité au terminal?",
    ],
    "rephrase:s3_timeline_checks": [
        "À quelle heure Samira a quitté la salle?",
        "Qui était près du couloir vers dix-huit heures?",
        "Pouvez-vous préciser l'ordre des déplacements?",
    ],
    "rephrase:s4_clothing_timestamp": [
        "Vers quelle heure avez-vous vu cette personne?",
        "Quels vêtements avez-vous remarqués d'abord?",
        "La personne est restée combien de minutes?",
    ],
    "rephrase:s5_accusation_logic": [
        "Je relie l'indice de temps et l'indice d'accès.",
        "Je présente d'abord la contradiction, puis la conclusion.",
        "Je propose une récupération discrète avec preuves.",
    ],
};

const EN_META_HELP_COPY: Record<string, string> = {
    "meta:s1_english_prompting": "Use a short French summary sentence. Keep one time marker and one object noun.",
    "meta:s2_english_polite_security": "Ask politely for process access in French; avoid imperative tone.",
    "meta:s3_english_timeline_frame": "Build summary as: time -> person -> place in French.",
    "meta:s4_english_witness_focus": "Lead with time, then clothing descriptor, then location in French.",
    "meta:s5_english_reasoning_frame": "State contradiction evidence first, then accusation/recovery intent in French.",
};

const SUMMARY_CODE_COPY: Record<string, string> = {
    summary_passed: "Summary accepted. Scene progression can continue.",
    summary_required: "A French summary is required before this action.",
    summary_needed: "Provide a French summary to complete this scene step.",
    summary_insufficient_facts: "Summary missing enough corroborated facts.",
    summary_missing_key_fact: "Summary missing a required key scene fact for this difficulty.",
};

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

    const render = (): void => {
        panel.innerHTML = "";
        if (!lastState || !lastState.dialogue) {
            panel.style.display = "none";
            return;
        }
        panel.style.display = "block";
        const dialogue = lastState.dialogue;

        const title = document.createElement("div");
        title.className = "dialogue-title";
        title.textContent = "Dialogue D'Enquete";
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

        renderSectionTitle(panel, "NPC State Card");
        renderNpcStateCard(panel, npcCardState);

        renderDataLines(panel, [
            ["Active scene", dialogue.active_scene_id ?? "none"],
            ["Focus scene", focusSceneId ?? "none"],
            ["Current NPC", npcCardState?.npc_id ?? focusNpcId ?? "unknown"],
            ["Known dialogue facts", String(dialogue.revealed_fact_ids.length)],
            ["Contradiction path", dialogue.contradiction_requirement_satisfied ? "satisfied" : "pending"],
        ]);
        renderLearningSlice(panel, dialogue);

        renderSectionTitle(panel, "Scene Progress");
        renderSceneProgress(panel, dialogue.scene_completion, dialogue.surfaced_scene_ids, focusSceneId);

        renderSectionTitle(panel, "Summary & Hint Ladder");
        renderSummaryHintSection(panel, {
            dialogue,
            focusSceneId,
            selectedIntent,
            requiredSlots,
        });

        renderSectionTitle(panel, "Action Composer");
        if (!focusSceneId || !sceneConfig || !focusNpcId) {
            renderInfo(panel, "No active or surfaced scene available for structured turn entry.");
        } else {
            const allowedIntents = sceneConfig.allowedIntents;

            renderIntentButtons(panel, {
                intents: allowedIntents,
                selectedIntent,
                onSelect: (intentId) => {
                    selectedIntent = intentId;
                    slotValues = syncSlotValues(slotValues, collectRequiredSlots(sceneConfig, selectedIntent));
                    render();
                },
            });

            renderSlotInputs(panel, {
                requiredSlots,
                values: slotValues,
                onChange: (slotName, value) => {
                    slotValues[slotName] = value;
                },
            });

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

            const minFacts = dialogue.summary_rules.current_scene_min_fact_count;
            const summaryRequired = dialogue.summary_rules.required_scene_ids.includes(focusSceneId);
            if (summaryRequired) {
                renderInfo(
                    panel,
                    `Summary required: ${minFacts ?? 1} accepted fact(s), target language FR.`
                );
            }

            const dispatchAvailable = opts.canDispatchDialogueTurn
                ? opts.canDispatchDialogueTurn()
                : Boolean(opts.dispatchDialogueTurn);
            const canSubmit = dispatchAvailable && !pending && selectedIntent !== null;
            const submitBtn = document.createElement("button");
            submitBtn.type = "button";
            submitBtn.className = "dialogue-submit";
            submitBtn.disabled = !canSubmit;
            submitBtn.textContent = pending ? "Sending..." : "Submit Structured Turn";
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
                renderInfo(panel, "Live dialogue dispatch unavailable in this mode; replay visualization remains active.");
            }
        }

        if (submitFeedback) {
            renderSectionTitle(panel, "Last Submission");
            renderDataLines(panel, [
                ["Tick", String(submitFeedback.tick)],
                ["Scene", submitFeedback.sceneId],
                ["Intent", submitFeedback.intentId],
                ["Status", `${submitFeedback.result.status}/${submitFeedback.result.code}`],
                ["Summary", submitFeedback.result.summary ?? "none"],
            ]);
        }

        renderSectionTitle(panel, "Recent Structured Turns");
        renderTranscript(panel, dialogue.recent_turns);
    };

    store.subscribe((state) => {
        lastState = state;
        render();
    });

    return {
        root,
        setInspectSelection: (selection) => {
            inspectSelection = selection;
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
            summary: "No dialogue dispatcher configured.",
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

function renderNpcStateCard(panel: HTMLElement, npc: KvpNpcSemanticState | null): void {
    if (!npc) {
        renderInfo(panel, "No visible NPC semantic state available.");
        return;
    }
    const card = document.createElement("div");
    card.className = "dialogue-npc-card";

    const portraitSlot = document.createElement("div");
    portraitSlot.className = "dialogue-npc-portrait";
    portraitSlot.textContent = `${npc.npc_id}\n${npc.card_state.portrait_variant}`;

    const meta = document.createElement("div");
    meta.className = "dialogue-npc-meta";
    appendNpcLine(meta, "Emotion", npc.emotion);
    appendNpcLine(meta, "Stance", npc.stance);
    appendNpcLine(meta, "Alignment", npc.soft_alignment_hint);
    appendNpcLine(meta, "Trust trend", npc.card_state.trust_trend);
    appendNpcLine(meta, "Tell cue", npc.card_state.tell_cue ?? "none");
    appendNpcLine(meta, "Suggested mode", npc.card_state.suggested_interaction_mode);
    appendNpcLine(meta, "Availability", npc.availability);

    card.append(portraitSlot, meta);
    panel.appendChild(card);
}

function renderLearningSlice(panel: HTMLElement, dialogue: NonNullable<WorldState["dialogue"]>): void {
    const learning = dialogue.learning;
    if (!learning) return;
    renderSectionTitle(panel, "Scaffolding");
    renderDataLines(panel, [
        ["Difficulty", learning.difficulty_profile],
        ["Hint level", learning.current_hint_level],
        ["Recommended mode", learning.scaffolding_policy.recommended_mode],
        ["FR required", learning.scaffolding_policy.french_action_required ? "yes" : "no"],
        ["Meta EN help", learning.scaffolding_policy.english_meta_allowed ? "yes" : "no"],
        ["Prompt generosity", learning.scaffolding_policy.prompt_generosity],
        ["Confirmation", learning.scaffolding_policy.confirmation_strength],
        ["Summary strictness", learning.scaffolding_policy.summary_strictness],
        ["Language support", learning.scaffolding_policy.language_support_level],
        ["Policy reason", learning.scaffolding_policy.reason_code],
    ]);
    const completedMgs = learning.minigames.filter((row) => row.completed).length;
    renderInfo(
        panel,
        `Minigames: ${completedMgs}/${learning.minigames.length} completed; target: ${learning.scaffolding_policy.target_minigame_id ?? "none"}`
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
        renderInfo(panel, "Learning projection unavailable for summary/hint surfaces.");
        return;
    }
    if (!opts.focusSceneId) {
        renderInfo(panel, "No focus scene for summary prompt.");
        return;
    }

    const summaryState = learning.summary_by_scene.find((row) => row.scene_id === opts.focusSceneId) ?? null;
    if (!summaryState) {
        renderInfo(panel, "No summary rule projection for current scene.");
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
        ? `yes (${summaryState.effective_min_fact_count} accepted fact(s) minimum)`
        : "no";
    renderDataLines(block, [
        ["Scene", sceneId],
        ["Summary state", summaryState.status],
        ["Summary required", requiredLabel],
        ["Strictness", summaryState.strictness_mode],
        ["Attempts", String(summaryState.attempt_count)],
    ]);

    const prompt = buildSummaryPrompt(sceneId, summaryState, selectedIntent, requiredSlots);
    const promptLine = document.createElement("div");
    promptLine.className = "dialogue-summary-prompt";
    promptLine.textContent = `Prompt: ${prompt}`;
    block.appendChild(promptLine);

    const feedback = resolveSummaryFeedback(summaryState, dialogue.recent_turns, sceneId);
    if (feedback) {
        const feedbackLine = document.createElement("div");
        feedbackLine.className = "dialogue-summary-feedback";
        feedbackLine.textContent = `Feedback: ${feedback}`;
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
    title.textContent = `Hint ladder (${learning.current_hint_level}, ${learning.difficulty_profile})`;
    ladder.appendChild(title);

    const policy = learning.scaffolding_policy;
    if (policy.scene_id && policy.scene_id !== sceneId) {
        renderInfo(ladder, `Policy currently tuned for scene ${policy.scene_id}; showing current projection.`);
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
        head.textContent = `${HINT_LEVEL_LABELS[level]} - ${isCurrent ? "current" : isAllowed ? "available" : "locked"}`;
        row.appendChild(head);

        const body = document.createElement("div");
        body.className = "dialogue-hint-body";
        body.textContent = resolveHintBody(level, policy, sceneId, requiredSlots, isAllowed);
        row.appendChild(body);

        ladder.appendChild(row);
    }
}

function buildSummaryPrompt(
    sceneId: string,
    summaryState: LearningSceneSummaryState,
    selectedIntent: string | null,
    requiredSlots: string[]
): string {
    const slotsLabel = requiredSlots.length > 0 ? `Include slots: ${requiredSlots.join(", ")}.` : "No mandatory slots.";
    const keyFactHint =
        summaryState.required_key_fact_ids.length > 0
            ? "Include at least one key scene fact that you have already confirmed."
            : "Use only facts you have already unlocked.";
    const intentLabel = selectedIntent ? `Intent context: ${selectedIntent}.` : "Intent context: none.";
    return `FR summary for ${sceneId}. ${slotsLabel} ${intentLabel} ${keyFactHint}`;
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
    if (!code) return summaryState.status === "passed" ? SUMMARY_CODE_COPY.summary_passed : null;
    return SUMMARY_CODE_COPY[code] ?? `Summary status: ${code}`;
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
            return "Not available at current difficulty/state.";
        }
        return "Locked until additional repair/summary pressure or easier difficulty support.";
    }

    if (level === "soft_hint") {
        return SOFT_HINT_COPY[policy.soft_hint_key ?? ""] ?? `Use scene ${sceneId} anchors before escalating.`;
    }
    if (level === "sentence_stem") {
        const base = SENTENCE_STEM_COPY[policy.sentence_stem_key ?? ""] ?? "Je résume: ___, ___, ___.";
        if (requiredSlots.length === 0) return base;
        return `${base} (Slots: ${requiredSlots.join(", ")})`;
    }
    if (level === "rephrase_choice") {
        const options = REPHRASE_CHOICES_COPY[policy.rephrase_set_id ?? ""];
        if (!options || options.length === 0) return "Rephrase your previous turn in shorter, more specific French.";
        return `Choose one: ${options.join(" / ")}`;
    }
    if (!policy.english_meta_allowed) {
        return "English meta-help unavailable at this difficulty/state.";
    }
    return EN_META_HELP_COPY[policy.english_meta_key ?? ""] ?? "English framing only; final action must remain in French.";
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
    focusSceneId: string | null
): void {
    const wrap = document.createElement("div");
    wrap.className = "dialogue-scene-list";
    panel.appendChild(wrap);

    const surfaced = new Set(surfacedSceneIds);
    for (const row of rows) {
        const item = document.createElement("div");
        item.className = "dialogue-scene-row";
        if (row.scene_id === focusSceneId) item.classList.add("is-focus");
        item.textContent = `${row.scene_id}  ${row.completion_state}${surfaced.has(row.scene_id) ? "  surfaced" : ""}`;
        wrap.appendChild(item);
    }
}

function renderIntentButtons(
    panel: HTMLElement,
    opts: {
        intents: string[];
        selectedIntent: string | null;
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
        btn.textContent = intentId;
        btn.addEventListener("click", () => opts.onSelect(intentId));
        wrap.appendChild(btn);
    }
}

function renderSlotInputs(
    panel: HTMLElement,
    opts: {
        requiredSlots: string[];
        values: Record<string, string>;
        onChange: (slotName: string, value: string) => void;
    }
): void {
    if (opts.requiredSlots.length === 0) {
        renderInfo(panel, "No required slots for this intent/scene combination.");
        return;
    }
    for (const slotName of opts.requiredSlots) {
        const row = document.createElement("label");
        row.className = "dialogue-input-row";
        const label = document.createElement("span");
        label.className = "dialogue-input-label";
        label.textContent = `slot:${slotName}`;
        const input = document.createElement("input");
        input.className = "dialogue-input";
        input.type = "text";
        input.value = opts.values[slotName] ?? "";
        input.placeholder = `enter ${slotName}`;
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
    const facts = renderAuxInput("presented_fact_ids (csv)", opts.factInput, "N1,N3", opts.onFactChange);
    const evidence = renderAuxInput(
        "presented_evidence_ids (csv)",
        opts.evidenceInput,
        "E2_CAFE_RECEIPT",
        opts.onEvidenceChange
    );
    const utterance = renderAuxInput(
        "utterance_text (optional)",
        opts.utteranceInput,
        "REGISTER:WRONG ...",
        opts.onUtteranceChange
    );
    panel.append(facts, evidence, utterance);
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

function renderTranscript(panel: HTMLElement, turns: KvpDialogueTurnLog[]): void {
    if (turns.length === 0) {
        renderInfo(panel, "No dialogue turns recorded in current projection.");
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
        line1.textContent = `#${turn.turn_index} ${turn.scene_id} ${turn.npc_id} ${turn.intent_id}`;
        const line2 = document.createElement("div");
        line2.className = "dialogue-turn-meta";
        line2.textContent = `${turn.status}/${turn.code}  mode:${turn.response_mode}`;
        row.append(line1, line2);

        if (turn.revealed_fact_ids.length > 0 || turn.summary_check_code || turn.repair_response_mode) {
            const detail = document.createElement("div");
            detail.className = "dialogue-turn-detail";
            detail.textContent =
                `facts:[${turn.revealed_fact_ids.join(", ")}]` +
                (turn.summary_check_code ? ` summary:${turn.summary_check_code}` : "") +
                (turn.repair_response_mode ? ` repair:${turn.repair_response_mode}` : "");
            row.appendChild(detail);
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
