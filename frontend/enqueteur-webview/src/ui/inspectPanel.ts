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
import {
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
};

export type InspectHandle = {
    root: HTMLElement;
    setSelection: (sel: InspectSelection) => void;
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
            if (!room) return renderMissing("Room", selection.id);
            renderRoom(panel, room);
            return;
        }

        if (selection.kind === "agent") {
            const agent = lastState.agents.get(selection.id);
            if (!agent) return renderMissing("Agent", selection.id);
            renderAgent(panel, agent, lastState);
            return;
        }

        if (selection.kind === "object") {
            const obj = lastState.objects.get(selection.id);
            if (!obj) return renderMissing("Object", selection.id);
            renderObjectActionPanel(panel, obj, lastState, {
                dispatchInvestigationAction: opts.dispatchInvestigationAction,
                canDispatchInvestigationAction: opts.canDispatchInvestigationAction,
                pendingActionKey,
                lastActionFeedback,
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
                                    summary: "Action dispatch is unavailable in this mode.",
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
        line.textContent = "No data available.";
        panel.appendChild(line);
    };

    store.subscribe((s) => {
        lastState = s;
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
        clear,
        getSelection: () => selection,
    };
}

function renderRoom(panel: HTMLElement, room: KvpRoom): void {
    const title = document.createElement("div");
    title.className = "inspect-title";
    title.textContent = room.label ?? `Room ${room.room_id}`;
    panel.appendChild(title);

    const lines: Array<[string, string]> = [
        ["Room", String(room.room_id)],
        ["Zone", room.zone ?? "unknown"],
        ["Level", room.level?.toString() ?? "0"],
        ["Kind", String(room.kind_code)],
        ["Tension", room.tension_tier ?? "none"],
        ["Occupants", String(room.occupants?.length ?? 0)],
    ];

    renderLines(panel, lines);
}

function renderAgent(panel: HTMLElement, agent: KvpAgent, state: WorldState): void {
    const title = document.createElement("div");
    title.className = "inspect-title";
    title.textContent = `Agent ${agent.agent_id}`;
    panel.appendChild(title);

    const roomLabel = state.rooms.get(agent.room_id)?.label ?? `Room ${agent.room_id}`;
    const activeObject = findObjectByOccupant(state, agent.agent_id);
    const context = activeObject ? `${activeObject.class_code} #${activeObject.object_id}` : "none";

    const lines: Array<[string, string]> = [
        ["Room", roomLabel],
        ["Role", String(agent.role_code)],
        ["Action", String(agent.action_state_code)],
        ["Generation", String(agent.generation)],
        ["Interacting", context],
    ];
    renderLines(panel, lines);

    if (state.npcSemantic.length > 0) {
        renderSectionTitle(panel, "Character Cues");
        renderLines(panel, [
            ["Visible profiles", String(state.npcSemantic.length)],
            ["Tip", "Select an object to view available actions."],
        ]);
    }
}

type RenderActionPanelOpts = {
    dispatchInvestigationAction?: InvestigationActionDispatcher;
    canDispatchInvestigationAction?: () => boolean;
    pendingActionKey: string | null;
    lastActionFeedback: LastActionFeedback | null;
    onAction: (request: InvestigationActionRequest) => Promise<void>;
};

function renderObjectActionPanel(
    panel: HTMLElement,
    obj: KvpObject,
    state: WorldState,
    opts: RenderActionPanelOpts
): void {
    const title = document.createElement("div");
    title.className = "inspect-title";
    title.textContent = `${obj.class_code}`;
    panel.appendChild(title);

    const roomLabel = state.rooms.get(obj.room_id)?.label ?? `Room ${obj.room_id}`;
    const occupant = obj.occupant_agent_id ? state.agents.get(obj.occupant_agent_id) : null;
    const occupantLabel = occupant ? `Agent ${occupant.agent_id}` : "none";
    renderLines(panel, [
        ["Object", String(obj.object_id)],
        ["Room", roomLabel],
        ["Status", String(obj.status_code)],
        ["Occupant", occupantLabel],
    ]);

    const caseObjectId = resolveCaseObjectId(obj, state);
    renderSectionTitle(panel, "Interaction");
    if (!caseObjectId) {
        renderLines(panel, [
            ["Case Object", "not mapped"],
            ["Reason", "This world object has no MBAM v1 affordance binding."],
        ]);
        return;
    }

    const investigationObject = state.investigation?.objects.find((row) => row.object_id === caseObjectId) ?? null;
    const objectGuide = getMbamObjectGuide(caseObjectId);
    renderLines(panel, [["Case Object", `${caseObjectId}${objectGuide ? ` (${objectGuide.label})` : ""}`]]);
    if (objectGuide) {
        renderLines(panel, [["Location hint", objectGuide.location_hint]]);
    }

    if (!investigationObject || !state.investigation) {
        renderLines(panel, [["Investigation State", "not available in current snapshot"]]);
        return;
    }

    renderLines(panel, [
        ["Affordances", String(investigationObject.affordances.length)],
        ["Observed", String(investigationObject.observed_affordances.length)],
        ["Evidence discovered", String(state.investigation.evidence.discovered_ids.length)],
        ["Evidence collected", String(state.investigation.evidence.collected_ids.length)],
        ["Facts known", String(state.investigation.facts.known_fact_ids.length)],
        ["Contradictions unlockable", String(state.investigation.contradictions.unlockable_edge_ids.length)],
    ]);
    renderObjectPrompt(panel, caseObjectId, state);

    renderKnownState(panel, investigationObject);
    renderActionButtons(panel, obj.object_id, caseObjectId, investigationObject, state, opts);
    renderLastActionFeedback(panel, obj.object_id, caseObjectId, opts.lastActionFeedback);
    renderRecentDialogueHint(panel, state);
}

function renderKnownState(panel: HTMLElement, objectState: KvpInvestigationObjectState): void {
    const entries = Object.entries(objectState.known_state ?? {}).sort(([a], [b]) => a.localeCompare(b));
    renderSectionTitle(panel, "Known Object State");
    if (entries.length === 0) {
        renderLines(panel, [["State", "No observed details yet"]]);
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
    renderSectionTitle(panel, "Actions");
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
            ? "Live action dispatch unavailable in replay/offline mode."
            : null;

        btn.disabled = isPending || !isDispatchAvailable;
        const actionLabel = labelMbamAction(affordanceId);
        btn.textContent = isPending ? `${actionLabel}...` : actionLabel;
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
            ? `Reviewed in this run (${affordanceId}).`
            : blockedReason
              ? blockedReason
              : `New lead: ${hintMbamAction(affordanceId)}`;
        actionsWrap.appendChild(info);
    }
}

function renderLastActionFeedback(
    panel: HTMLElement,
    worldObjectId: number,
    caseObjectId: string,
    feedback: LastActionFeedback | null
): void {
    if (!feedback) return;
    const expectedSelectionKey = selectionKeyForObject(worldObjectId, caseObjectId);
    if (feedback.selectionKey !== expectedSelectionKey) return;

    renderSectionTitle(panel, "Last Action Result");
    renderLines(panel, [
        ["Affordance", `${labelMbamAction(feedback.affordanceId)} (${feedback.affordanceId})`],
        ["Status", feedback.result.status],
        ["Code", feedback.result.code],
        ["Tick", String(feedback.tick)],
        ["Summary", feedback.result.summary ?? "none"],
        ["Guidance", describeInvestigationFeedback(feedback.result)],
        ["Facts", String(feedback.result.revealed_fact_ids?.length ?? 0)],
        ["Evidence", String(feedback.result.revealed_evidence_ids?.length ?? 0)],
    ]);
}

function renderRecentDialogueHint(panel: HTMLElement, state: WorldState): void {
    const dialogue = state.dialogue;
    if (!dialogue || dialogue.recent_turns.length === 0) return;
    const recent = dialogue.recent_turns[dialogue.recent_turns.length - 1] as KvpDialogueTurnLog;
    renderSectionTitle(panel, "Recent Dialogue Context");
    renderLines(panel, [
        ["Scene", recent.scene_id],
        ["Intent", recent.intent_id],
        ["Turn status", `${recent.status}/${recent.code}`],
    ]);
}

function renderObjectPrompt(panel: HTMLElement, caseObjectId: string, state: WorldState): void {
    const onboarding = buildMbamOnboardingView(state);
    const promptByObject: Record<string, string> = {
        O1_DISPLAY_CASE: "Starter lead: inspect + check lock to confirm what changed in the gallery.",
        O3_WALL_LABEL: "Read and note title/date. It helps anchor timeline dialogue.",
        O6_BADGE_TERMINAL: "Badge logs provide movement timing for contradiction checks.",
        O9_RECEIPT_PRINTER: "Receipt time helps corroborate witness statements.",
    };
    renderSectionTitle(panel, "Field Prompt");
    const note = document.createElement("div");
    note.className = "inspect-note";
    note.textContent = promptByObject[caseObjectId] ?? onboarding.currentLead;
    panel.appendChild(note);
    if (state.investigation?.contradictions.required_for_accusation && !state.investigation.contradictions.requirement_satisfied) {
        const contradictionNote = document.createElement("div");
        contradictionNote.className = "inspect-note";
        contradictionNote.textContent =
            "Contradiction path active: timeline-friendly object actions are especially valuable before accusation.";
        panel.appendChild(contradictionNote);
    }
}

function describeInvestigationFeedback(result: InvestigationActionResult): string {
    if (result.status === "accepted") {
        if (result.code === "projection_affordance_observed") {
            return "Action registered. Review newly observed clues and continue with other new leads.";
        }
        if (result.code === "projection_state_changed") {
            return "State changed. Cross-check Case Notes and timeline clues.";
        }
        return "Command accepted. Wait for live projection updates.";
    }
    if (result.status === "submitted") {
        return "Command accepted; waiting for authoritative diff.";
    }
    if (result.status === "unavailable") {
        return "Live runtime is unavailable. Reconnect and retry.";
    }
    if (result.status === "invalid") {
        return "Invalid action payload for current object. Use listed actions only.";
    }
    if (result.code === "SCENE_GATE_BLOCKED") {
        return "Blocked by scene gate. Advance dialogue or gather more clues first.";
    }
    if (result.code === "OBJECT_ACTION_UNAVAILABLE") {
        return "This action is currently blocked for this object state. Try another lead.";
    }
    if (result.code === "RUNTIME_NOT_READY") {
        return "Runtime not ready. Wait for sync and retry.";
    }
    return result.summary ?? "Action blocked by live runtime.";
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

function renderSectionTitle(panel: HTMLElement, text: string): void {
    const title = document.createElement("div");
    title.className = "inspect-subtitle";
    title.textContent = text;
    panel.appendChild(title);
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
