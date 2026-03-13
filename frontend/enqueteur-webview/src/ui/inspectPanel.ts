// src/ui/inspectPanel.ts
import type {
    WorldStore,
    WorldState,
    KvpAgent,
    KvpDialogueTurnLog,
    KvpInvestigationObjectState,
    KvpObject,
    KvpRoom,
} from "../state/worldStore";
import { createScopedTranslator, getSharedLocaleStore } from "../i18n";
import { resolvePresentationText } from "../app/presentationText";
import {
    buildMbamCaseSetupGuide,
    buildMbamOnboardingView,
    getMbamObjectGuide,
    hintMbamAction,
    labelMbamAction,
} from "./mbamOnboarding";

export type InspectSelection =
    | { kind: "room"; id: number }
    | { kind: "agent"; id: number }
    | { kind: "object"; id: number }
    | null;

export type InvestigationActionRequest = {
    worldObjectId: number;
    caseObjectId: string;
    affordanceId: string;
    tick: number;
};

export type InvestigationActionResult = {
    status: "submitted" | "accepted" | "blocked" | "invalid" | "unavailable" | "error";
    code: string;
    summary?: string;
    revealed_fact_ids?: string[];
    revealed_evidence_ids?: string[];
};

export type InvestigationActionDispatcher = (
    request: InvestigationActionRequest
) => Promise<InvestigationActionResult> | InvestigationActionResult;

export type InspectPanelOpts = {
    dispatchInvestigationAction?: InvestigationActionDispatcher;
    canDispatchInvestigationAction?: () => boolean;
    presentationProfile?: "demo" | "playtest" | "dev";
};

export type InspectHandle = {
    root: HTMLElement;
    setSelection: (sel: InspectSelection) => void;
    setPresentationProfile?: (profile: "demo" | "playtest" | "dev") => void;
    clear: () => void;
    getSelection: () => InspectSelection;
};

type LastActionFeedback = {
    selectionKey: string;
    caseObjectId: string;
    affordanceId: string;
    result: InvestigationActionResult;
    tick: number;
};

const WORLD_OBJECT_TO_CASE_OBJECT: Record<number, string> = {
    3002: "O1_DISPLAY_CASE",
    3003: "O4_BENCH",
    3004: "O6_BADGE_TERMINAL",
    3007: "O9_RECEIPT_PRINTER",
    3008: "O10_BULLETIN_BOARD",
};

const WORLD_CLASS_TO_CASE_OBJECT: Record<string, string> = {
    DISPLAY_CASE: "O1_DISPLAY_CASE",
    BENCH: "O4_BENCH",
    SECURITY_TERMINAL: "O6_BADGE_TERMINAL",
    RECEIPT_PRINTER: "O9_RECEIPT_PRINTER",
    BULLETIN_BOARD: "O10_BULLETIN_BOARD",
};

const localeStore = getSharedLocaleStore();
const t = createScopedTranslator(() => localeStore.getLocale());

export function mountInspectPanel(store: WorldStore, opts: InspectPanelOpts = {}): InspectHandle {
    const root = document.createElement("div");
    root.className = "inspect-root";

    const panel = document.createElement("div");
    panel.className = "inspect-panel";
    root.appendChild(panel);

    let selection: InspectSelection = null;
    let lastState: WorldState | null = null;
    let lastActionFeedback: LastActionFeedback | null = null;
    let pendingActionKey: string | null = null;
    let presentationProfile: "demo" | "playtest" | "dev" = opts.presentationProfile ?? "playtest";

    const render = (): void => {
        if (!selection || !lastState) {
            panel.style.display = "none";
            panel.innerHTML = "";
            return;
        }
        panel.style.display = "block";
        panel.innerHTML = "";

        if (selection.kind === "room") {
            const room = lastState.rooms.get(selection.id);
            if (!room) return renderMissing(t("inspect.missing.room"), selection.id);
            renderRoom(panel, room, presentationProfile !== "demo");
            return;
        }

        if (selection.kind === "agent") {
            const agent = lastState.agents.get(selection.id);
            if (!agent) return renderMissing(t("inspect.missing.agent"), selection.id);
            renderAgent(panel, agent, lastState, presentationProfile !== "demo");
            return;
        }

        if (selection.kind === "object") {
            const obj = lastState.objects.get(selection.id);
            if (!obj) return renderMissing(t("inspect.missing.object"), selection.id);
            renderObjectActionPanel(panel, obj, lastState, {
                dispatchInvestigationAction: opts.dispatchInvestigationAction,
                canDispatchInvestigationAction: opts.canDispatchInvestigationAction,
                pendingActionKey,
                lastActionFeedback,
                detailed: presentationProfile !== "demo",
                onAction: async (request) => {
                    const actionKey = `${selectionKeyForObject(request.worldObjectId, request.caseObjectId)}:${request.affordanceId}`;
                    pendingActionKey = actionKey;
                    render();

                    try {
                        const dispatch = opts.dispatchInvestigationAction;
                        if (!dispatch) {
                            lastActionFeedback = {
                                selectionKey: selectionKeyForObject(request.worldObjectId, request.caseObjectId),
                                caseObjectId: request.caseObjectId,
                                affordanceId: request.affordanceId,
                                tick: request.tick,
                                result: {
                                    status: "unavailable",
                                    code: "dispatch_unavailable",
                                    summary: t("inspect.action.dispatch_unavailable"),
                                },
                            };
                        } else {
                            const result = await dispatch(request);
                            lastActionFeedback = {
                                selectionKey: selectionKeyForObject(request.worldObjectId, request.caseObjectId),
                                caseObjectId: request.caseObjectId,
                                affordanceId: request.affordanceId,
                                tick: request.tick,
                                result,
                            };
                        }
                    } catch (err: unknown) {
                        const message = err instanceof Error ? err.message : String(err);
                        lastActionFeedback = {
                            selectionKey: selectionKeyForObject(request.worldObjectId, request.caseObjectId),
                            caseObjectId: request.caseObjectId,
                            affordanceId: request.affordanceId,
                            tick: request.tick,
                            result: {
                                status: "error",
                                code: "dispatch_error",
                                summary: message,
                            },
                        };
                    } finally {
                        pendingActionKey = null;
                        render();
                    }
                },
            });
            return;
        }
    };

    const renderMissing = (label: string, id: number): void => {
        const title = document.createElement("div");
        title.className = "inspect-title";
        title.textContent = `${label} ${id}`;
        panel.appendChild(title);
        const line = document.createElement("div");
        line.className = "inspect-line";
        line.textContent = t("inspect.missing.body");
        panel.appendChild(line);
    };

    store.subscribe((s) => {
        lastState = s;
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

    const setSelection = (sel: InspectSelection): void => {
        selection = sel;
        render();
    };

    const clear = (): void => {
        setSelection(null);
    };

    document.addEventListener("pointerdown", (ev) => {
        if (!selection) return;
        const target = ev.target as Node | null;
        if (!target) return;
        if (panel.contains(target)) return;
        clear();
    });

    return {
        root,
        setSelection,
        setPresentationProfile: (profile) => {
            presentationProfile = profile;
            render();
        },
        clear,
        getSelection: () => selection,
    };
}

function renderRoom(panel: HTMLElement, room: KvpRoom, detailed: boolean): void {
    const title = document.createElement("div");
    title.className = "inspect-title";
    const roomLabel = resolveRoomLabel(room);
    title.textContent = roomLabel ?? t("inspect.title.room_with_id", { id: room.room_id });
    panel.appendChild(title);

    const lines: Array<[string, string]> = detailed
        ? [
            [t("inspect.line.room"), String(room.room_id)],
            [t("inspect.line.zone"), room.zone ?? t("inspect.value.unknown")],
            [t("inspect.line.level"), room.level?.toString() ?? "0"],
            [t("inspect.line.kind"), String(room.kind_code)],
            [t("inspect.line.tension"), room.tension_tier ?? t("inspect.value.none")],
            [t("inspect.line.occupants"), String(room.occupants?.length ?? 0)],
        ]
        : [
            [t("inspect.line.area"), humanizeClassCode(room.zone ?? "gallery")],
            [t("inspect.line.tension"), room.tension_tier ?? t("inspect.value.steady")],
            [t("inspect.line.people_nearby"), String(room.occupants?.length ?? 0)],
        ];

    renderLines(panel, lines);
}

function renderAgent(
    panel: HTMLElement,
    agent: KvpAgent,
    state: WorldState,
    detailed: boolean
): void {
    const title = document.createElement("div");
    title.className = "inspect-title";
    title.textContent = detailed
        ? t("inspect.title.character_with_id", { id: agent.agent_id })
        : t("inspect.title.character");
    panel.appendChild(title);

    const roomLabel = resolveRoomLabel(state.rooms.get(agent.room_id))
        ?? t("inspect.title.room_with_id", { id: agent.room_id });
    const activeObject = findObjectByOccupant(state, agent.agent_id);
    const context = describeInteractionContext(activeObject, detailed);

    const lines: Array<[string, string]> = detailed
        ? [
            [t("inspect.line.room"), roomLabel],
            [t("inspect.line.role"), String(agent.role_code)],
            [t("inspect.line.action"), String(agent.action_state_code)],
            [t("inspect.line.generation"), String(agent.generation)],
            [t("inspect.line.interacting"), context],
        ]
        : [
            [t("inspect.line.room"), roomLabel],
            [t("inspect.line.interacting"), context],
        ];
    renderLines(panel, lines);

    if (state.npcSemantic.length > 0) {
        renderSectionTitle(panel, t("inspect.section.character_notes"));
        renderLines(panel, [
            [t("inspect.line.profiles_in_view"), String(state.npcSemantic.length)],
            [t("inspect.line.tip"), t("inspect.tip.select_object")],
        ]);
    }
}

type RenderActionPanelOpts = {
    dispatchInvestigationAction?: InvestigationActionDispatcher;
    canDispatchInvestigationAction?: () => boolean;
    pendingActionKey: string | null;
    lastActionFeedback: LastActionFeedback | null;
    detailed: boolean;
    onAction: (request: InvestigationActionRequest) => Promise<void>;
};

function renderObjectActionPanel(
    panel: HTMLElement,
    obj: KvpObject,
    state: WorldState,
    opts: RenderActionPanelOpts
): void {
    const caseObjectId = resolveCaseObjectId(obj, state);
    const objectGuide = caseObjectId ? getMbamObjectGuide(caseObjectId) : null;

    const title = document.createElement("div");
    title.className = "inspect-title";
    title.textContent = opts.detailed
        ? `${obj.class_code}`
        : (objectGuide?.label ?? humanizeClassCode(obj.class_code));
    panel.appendChild(title);

    const roomLabel = resolveRoomLabel(state.rooms.get(obj.room_id))
        ?? t("inspect.title.room_with_id", { id: obj.room_id });
    const occupant = obj.occupant_agent_id ? state.agents.get(obj.occupant_agent_id) : null;
    const occupantLabel = opts.detailed
        ? (occupant ? t("inspect.value.agent_with_id", { id: occupant.agent_id }) : t("inspect.value.none"))
        : (occupant ? t("inspect.value.someone_nearby") : t("inspect.value.no_one_nearby"));
    if (opts.detailed) {
        renderLines(panel, [
            [t("inspect.line.object"), String(obj.object_id)],
            [t("inspect.line.room"), roomLabel],
            [t("inspect.line.status"), String(obj.status_code)],
            [t("inspect.line.occupant"), occupantLabel],
        ]);
    } else {
        renderLines(panel, [
            [t("inspect.line.room"), roomLabel],
            [t("inspect.line.occupant"), occupantLabel],
        ]);
    }

    renderSectionTitle(panel, t("inspect.section.investigation_actions"));
    if (!caseObjectId) {
        renderInfo(panel, opts.detailed
            ? t("inspect.info.object_link_unavailable")
            : t("inspect.info.no_direct_action"));
        return;
    }

    const investigationObject = state.investigation?.objects.find((row) => row.object_id === caseObjectId) ?? null;
    renderLines(panel, [[
        opts.detailed ? t("inspect.line.case_object") : t("inspect.line.object"),
        opts.detailed
            ? `${caseObjectId}${objectGuide ? ` (${objectGuide.label})` : ""}`
            : (objectGuide?.label ?? caseObjectId),
    ]]);
    if (objectGuide) {
        renderLines(panel, [[
            opts.detailed ? t("inspect.line.location_hint") : t("inspect.line.where_to_look"),
            objectGuide.location_hint,
        ]]);
    }

    if (!investigationObject || !state.investigation) {
        renderLines(panel, [[t("inspect.line.investigation_notes"), t("inspect.value.loading")]]);
        return;
    }

    renderLines(panel, opts.detailed
        ? [
            [t("inspect.line.available_actions"), String(investigationObject.affordances.length)],
            [t("inspect.line.actions_reviewed"), String(investigationObject.observed_affordances.length)],
            [t("inspect.line.evidence_found"), String(state.investigation.evidence.discovered_ids.length)],
            [t("inspect.line.evidence_collected"), String(state.investigation.evidence.collected_ids.length)],
            [t("inspect.line.facts_learned"), String(state.investigation.facts.known_fact_ids.length)],
            [t("inspect.line.contradiction_leads"), String(state.investigation.contradictions.unlockable_edge_ids.length)],
        ]
        : [
            [t("inspect.line.leads_available"), String(investigationObject.affordances.length)],
            [t("inspect.line.leads_checked"), String(investigationObject.observed_affordances.length)],
            [t("inspect.line.clues_found"), String(state.investigation.evidence.discovered_ids.length)],
            [t("inspect.line.clues_secured"), String(state.investigation.evidence.collected_ids.length)],
            [t("inspect.line.facts_confirmed"), String(state.investigation.facts.known_fact_ids.length)],
            [t("inspect.line.timeline_tensions"), String(state.investigation.contradictions.unlockable_edge_ids.length)],
        ]);
    renderObjectPrompt(panel, caseObjectId, state);

    renderKnownState(panel, investigationObject, opts.detailed);
    renderActionButtons(panel, obj.object_id, caseObjectId, investigationObject, state, opts);
    renderLastActionFeedback(panel, obj.object_id, caseObjectId, opts.lastActionFeedback, opts.detailed);
    renderRecentDialogueHint(panel, state, opts.detailed);
}

function resolveRoomLabel(room: KvpRoom | undefined): string | null {
    if (!room) return null;
    return resolvePresentationText({
        text: room.label,
        textKey: room.label_key,
        fallbackText: t("inspect.title.room_with_id", { id: room.room_id }),
    });
}

function renderKnownState(
    panel: HTMLElement,
    objectState: KvpInvestigationObjectState,
    detailed: boolean
): void {
    if (!detailed) {
        renderSectionTitle(panel, t("inspect.section.known_object_state"));
        const keyCount = Object.keys(objectState.known_state ?? {}).length;
        renderLines(panel, [[
            t("inspect.line.visible_clues"),
            keyCount > 0 ? String(keyCount) : t("inspect.value.none_yet"),
        ]]);
        return;
    }
    const entries = Object.entries(objectState.known_state ?? {}).sort(([a], [b]) => a.localeCompare(b));
    renderSectionTitle(panel, t("inspect.section.known_object_state"));
    if (entries.length === 0) {
        renderLines(panel, [[t("inspect.line.state"), t("inspect.value.no_observed_details")]]);
        return;
    }
    renderLines(
        panel,
        entries.map(([key, value]) => [key, stringifyValue(value)])
    );
}

function renderActionButtons(
    panel: HTMLElement,
    worldObjectId: number,
    caseObjectId: string,
    objectState: KvpInvestigationObjectState,
    state: WorldState,
    opts: RenderActionPanelOpts
): void {
    renderSectionTitle(panel, t("inspect.section.actions"));
    const actionsWrap = document.createElement("div");
    actionsWrap.className = "inspect-actions";
    panel.appendChild(actionsWrap);

    const orderedAffordances = [...objectState.affordances].sort((a, b) => {
        const aObserved = objectState.observed_affordances.includes(a);
        const bObserved = objectState.observed_affordances.includes(b);
        if (aObserved === bObserved) return a.localeCompare(b);
        return aObserved ? 1 : -1;
    });

    for (const affordanceId of orderedAffordances) {
        const actionKey = `${selectionKeyForObject(worldObjectId, caseObjectId)}:${affordanceId}`;
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "inspect-action-btn";

        const isPending = opts.pendingActionKey === actionKey;
        const isDispatchAvailable = opts.canDispatchInvestigationAction
            ? opts.canDispatchInvestigationAction()
            : Boolean(opts.dispatchInvestigationAction);
        const blockedReason = !isDispatchAvailable
            ? t("inspect.action.sending_unavailable")
            : null;

        btn.disabled = isPending || !isDispatchAvailable;
        const actionLabel = labelMbamAction(affordanceId);
        btn.textContent = isPending
            ? t("inspect.action.pending_label", { action: actionLabel })
            : actionLabel;
        btn.addEventListener("click", () => {
            void opts.onAction({
                worldObjectId,
                caseObjectId,
                affordanceId,
                tick: state.tick,
            });
        });
        actionsWrap.appendChild(btn);

        const observed = objectState.observed_affordances.includes(affordanceId);
        const info = document.createElement("div");
        info.className = "inspect-note";
        info.textContent = observed
            ? t("inspect.info.already_checked")
            : blockedReason
              ? blockedReason
              : t("inspect.info.new_lead", { hint: hintMbamAction(affordanceId) });
        actionsWrap.appendChild(info);
    }
}

function renderLastActionFeedback(
    panel: HTMLElement,
    worldObjectId: number,
    caseObjectId: string,
    feedback: LastActionFeedback | null,
    detailed: boolean
): void {
    if (!feedback) return;
    const expectedSelectionKey = selectionKeyForObject(worldObjectId, caseObjectId);
    if (feedback.selectionKey !== expectedSelectionKey) return;

    renderSectionTitle(panel, t("inspect.section.latest_result"));
    renderLines(panel, detailed
        ? [
            [t("inspect.line.affordance"), `${labelMbamAction(feedback.affordanceId)} (${feedback.affordanceId})`],
            [t("inspect.line.status"), feedback.result.status],
            [t("inspect.line.code"), feedback.result.code],
            [t("inspect.line.tick"), String(feedback.tick)],
            [t("inspect.line.summary"), feedback.result.summary ?? t("inspect.value.none")],
            [t("inspect.line.next_step"), describeInvestigationFeedback(feedback.result)],
            [t("inspect.line.facts"), String(feedback.result.revealed_fact_ids?.length ?? 0)],
            [t("inspect.line.evidence"), String(feedback.result.revealed_evidence_ids?.length ?? 0)],
        ]
        : [
            [t("inspect.line.action"), labelMbamAction(feedback.affordanceId)],
            [t("inspect.line.result"), feedback.result.status],
            [t("inspect.line.summary"), feedback.result.summary ?? describeInvestigationFeedback(feedback.result)],
        ]);
}

function renderRecentDialogueHint(panel: HTMLElement, state: WorldState, detailed: boolean): void {
    const dialogue = state.dialogue;
    if (!dialogue || dialogue.recent_turns.length === 0) return;
    const recent = dialogue.recent_turns[dialogue.recent_turns.length - 1] as KvpDialogueTurnLog;
    renderSectionTitle(panel, t("inspect.section.recent_conversation"));
    renderLines(panel, detailed
        ? [
            [t("inspect.line.scene"), recent.scene_id],
            [t("inspect.line.intent"), recent.intent_id],
            [t("inspect.line.result"), `${recent.status}/${recent.code}`],
        ]
        : [
            [t("inspect.line.scene"), labelSceneFromId(recent.scene_id)],
            [t("inspect.line.result"), formatConversationResult(recent.status)],
        ]);
}

function renderObjectPrompt(panel: HTMLElement, caseObjectId: string, state: WorldState): void {
    const onboarding = buildMbamOnboardingView(state);
    const setupGuide = buildMbamCaseSetupGuide(state);
    const promptByObject: Record<string, string> = {
        O1_DISPLAY_CASE: t("inspect.prompt.O1_DISPLAY_CASE"),
        O3_WALL_LABEL: t("inspect.prompt.O3_WALL_LABEL"),
        O6_BADGE_TERMINAL: t("inspect.prompt.O6_BADGE_TERMINAL"),
        O9_RECEIPT_PRINTER: t("inspect.prompt.O9_RECEIPT_PRINTER"),
    };
    renderSectionTitle(panel, t("inspect.section.field_prompt"));
    const note = document.createElement("div");
    note.className = "inspect-note";
    note.textContent = promptByObject[caseObjectId] ?? onboarding.currentLead;
    panel.appendChild(note);

    const starterIds = ["O1_DISPLAY_CASE", "O3_WALL_LABEL"];
    const starterComplete = starterIds.every((objectId) => isInvestigationObjectObserved(state, objectId));
    if (!starterComplete) {
        const starterNote = document.createElement("div");
        starterNote.className = "inspect-note";
        starterNote.textContent = starterIds.includes(caseObjectId)
            ? t("inspect.info.priority_start_object")
            : t("inspect.info.first_pass_starters");
        panel.appendChild(starterNote);
    } else if ((state.dialogue?.recent_turns.length ?? 0) === 0) {
        const talkNote = document.createElement("div");
        talkNote.className = "inspect-note";
        talkNote.textContent = t("inspect.info.next_step", { step: setupGuide.firstTalkTo });
        panel.appendChild(talkNote);
    }

    if (state.investigation?.contradictions.required_for_accusation && !state.investigation.contradictions.requirement_satisfied) {
        const contradictionNote = document.createElement("div");
        contradictionNote.className = "inspect-note";
        contradictionNote.textContent =
            t("inspect.info.contradiction_priority");
        panel.appendChild(contradictionNote);
    }
}

function describeInvestigationFeedback(result: InvestigationActionResult): string {
    if (result.status === "accepted") {
        if (result.code === "projection_affordance_observed") {
            return t("inspect.feedback.action_confirmed");
        }
        if (result.code === "projection_state_changed") {
            return t("inspect.feedback.state_changed");
        }
        return t("inspect.feedback.accepted");
    }
    if (result.status === "submitted") {
        return t("inspect.feedback.submitted");
    }
    if (result.status === "unavailable") {
        return t("inspect.feedback.connection_not_ready");
    }
    if (result.status === "invalid") {
        return t("inspect.feedback.invalid");
    }
    if (result.code === "SCENE_GATE_BLOCKED") {
        return t("inspect.feedback.scene_gate_blocked");
    }
    if (result.code === "OBJECT_ACTION_UNAVAILABLE") {
        return t("inspect.feedback.object_action_unavailable");
    }
    if (result.code === "RUNTIME_NOT_READY") {
        return t("inspect.feedback.runtime_not_ready");
    }
    return result.summary ?? t("inspect.feedback.blocked_default");
}

function resolveCaseObjectId(obj: KvpObject, state: WorldState): string | null {
    const byExactId = WORLD_OBJECT_TO_CASE_OBJECT[obj.object_id];
    if (byExactId) return byExactId;

    const byClassCode = WORLD_CLASS_TO_CASE_OBJECT[obj.class_code];
    if (!byClassCode) return null;

    if (!state.investigation) return byClassCode;
    return state.investigation.objects.some((row) => row.object_id === byClassCode) ? byClassCode : null;
}

function selectionKeyForObject(worldObjectId: number, caseObjectId: string): string {
    return `object:${worldObjectId}:${caseObjectId}`;
}

function stringifyValue(value: unknown): string {
    if (Array.isArray(value)) return value.join(", ");
    if (typeof value === "object" && value !== null) return JSON.stringify(value);
    return String(value);
}

function describeInteractionContext(activeObject: KvpObject | null, detailed: boolean): string {
    if (!activeObject) return t("inspect.value.none");
    if (detailed) return `${activeObject.class_code} #${activeObject.object_id}`;
    return humanizeClassCode(activeObject.class_code);
}

function humanizeClassCode(value: string): string {
    const normalized = value.replace(/_/g, " ").trim().toLowerCase();
    if (normalized.length === 0) return value;
    return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function labelSceneFromId(sceneId: string): string {
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

function formatConversationResult(status: string): string {
    if (status.length === 0) return t("inspect.value.pending");
    return status.charAt(0).toUpperCase() + status.slice(1);
}

function renderSectionTitle(panel: HTMLElement, text: string): void {
    const title = document.createElement("div");
    title.className = "inspect-subtitle";
    title.textContent = text;
    panel.appendChild(title);
}

function renderInfo(panel: HTMLElement, text: string): void {
    const line = document.createElement("div");
    line.className = "inspect-note";
    line.textContent = text;
    panel.appendChild(line);
}

function renderLines(panel: HTMLElement, lines: Array<[string, string]>): void {
    for (const [label, value] of lines) {
        const row = document.createElement("div");
        row.className = "inspect-line";
        const labelEl = document.createElement("span");
        labelEl.className = "inspect-label";
        labelEl.textContent = label;
        const valueEl = document.createElement("span");
        valueEl.className = "inspect-value";
        valueEl.textContent = value;
        row.append(labelEl, valueEl);
        panel.appendChild(row);
    }
}

function findObjectByOccupant(state: WorldState, agentId: number): KvpObject | null {
    for (const obj of state.objects.values()) {
        if (obj.occupant_agent_id === agentId) return obj;
    }
    return null;
}

function isInvestigationObjectObserved(state: WorldState, objectId: string): boolean {
    const objectRow = state.investigation?.objects.find((row) => row.object_id === objectId);
    if (!objectRow) return false;
    return objectRow.observed_affordances.length > 0;
}
