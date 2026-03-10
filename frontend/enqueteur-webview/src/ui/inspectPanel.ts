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
            if (!room) return renderMissing("Room", selection.id);
            renderRoom(panel, room, presentationProfile !== "demo");
            return;
        }

        if (selection.kind === "agent") {
            const agent = lastState.agents.get(selection.id);
            if (!agent) return renderMissing("Agent", selection.id);
            renderAgent(panel, agent, lastState, presentationProfile !== "demo");
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
                                    summary: "This action cannot be sent right now.",
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
        line.textContent = "Nothing to inspect here yet.";
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
    title.textContent = room.label ?? `Room ${room.room_id}`;
    panel.appendChild(title);

    const lines: Array<[string, string]> = detailed
        ? [
            ["Room", String(room.room_id)],
            ["Zone", room.zone ?? "unknown"],
            ["Level", room.level?.toString() ?? "0"],
            ["Kind", String(room.kind_code)],
            ["Tension", room.tension_tier ?? "none"],
            ["Occupants", String(room.occupants?.length ?? 0)],
        ]
        : [
            ["Area", humanizeClassCode(room.zone ?? "gallery")],
            ["Tension", room.tension_tier ?? "steady"],
            ["People nearby", String(room.occupants?.length ?? 0)],
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
    title.textContent = detailed ? `Character ${agent.agent_id}` : "Character";
    panel.appendChild(title);

    const roomLabel = state.rooms.get(agent.room_id)?.label ?? `Room ${agent.room_id}`;
    const activeObject = findObjectByOccupant(state, agent.agent_id);
    const context = describeInteractionContext(activeObject, detailed);

    const lines: Array<[string, string]> = detailed
        ? [
            ["Room", roomLabel],
            ["Role", String(agent.role_code)],
            ["Action", String(agent.action_state_code)],
            ["Generation", String(agent.generation)],
            ["Interacting", context],
        ]
        : [
            ["Room", roomLabel],
            ["Interacting", context],
        ];
    renderLines(panel, lines);

    if (state.npcSemantic.length > 0) {
        renderSectionTitle(panel, "Character Notes");
        renderLines(panel, [
            ["Profiles in view", String(state.npcSemantic.length)],
            ["Tip", "Select an object to see what you can do next."],
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

    const roomLabel = state.rooms.get(obj.room_id)?.label ?? `Room ${obj.room_id}`;
    const occupant = obj.occupant_agent_id ? state.agents.get(obj.occupant_agent_id) : null;
    const occupantLabel = opts.detailed
        ? (occupant ? `Agent ${occupant.agent_id}` : "none")
        : (occupant ? "Someone nearby" : "No one nearby");
    if (opts.detailed) {
        renderLines(panel, [
            ["Object", String(obj.object_id)],
            ["Room", roomLabel],
            ["Status", String(obj.status_code)],
            ["Occupant", occupantLabel],
        ]);
    } else {
        renderLines(panel, [
            ["Room", roomLabel],
            ["Occupant", occupantLabel],
        ]);
    }

    renderSectionTitle(panel, "Investigation Actions");
    if (!caseObjectId) {
        renderInfo(panel, opts.detailed
            ? "Object link not available. This object is not interactable in this case."
            : "No direct case action is available on this object right now.");
        return;
    }

    const investigationObject = state.investigation?.objects.find((row) => row.object_id === caseObjectId) ?? null;
    renderLines(panel, [[
        opts.detailed ? "Case Object" : "Object",
        opts.detailed
            ? `${caseObjectId}${objectGuide ? ` (${objectGuide.label})` : ""}`
            : (objectGuide?.label ?? caseObjectId),
    ]]);
    if (objectGuide) {
        renderLines(panel, [[opts.detailed ? "Location hint" : "Where to look", objectGuide.location_hint]]);
    }

    if (!investigationObject || !state.investigation) {
        renderLines(panel, [["Investigation Notes", "loading"]]);
        return;
    }

    renderLines(panel, opts.detailed
        ? [
            ["Available actions", String(investigationObject.affordances.length)],
            ["Actions reviewed", String(investigationObject.observed_affordances.length)],
            ["Evidence found", String(state.investigation.evidence.discovered_ids.length)],
            ["Evidence collected", String(state.investigation.evidence.collected_ids.length)],
            ["Facts learned", String(state.investigation.facts.known_fact_ids.length)],
            ["Contradiction leads", String(state.investigation.contradictions.unlockable_edge_ids.length)],
        ]
        : [
            ["Leads available", String(investigationObject.affordances.length)],
            ["Leads checked", String(investigationObject.observed_affordances.length)],
            ["Clues found", String(state.investigation.evidence.discovered_ids.length)],
            ["Clues secured", String(state.investigation.evidence.collected_ids.length)],
            ["Facts confirmed", String(state.investigation.facts.known_fact_ids.length)],
            ["Timeline tensions", String(state.investigation.contradictions.unlockable_edge_ids.length)],
        ]);
    renderObjectPrompt(panel, caseObjectId, state);

    renderKnownState(panel, investigationObject, opts.detailed);
    renderActionButtons(panel, obj.object_id, caseObjectId, investigationObject, state, opts);
    renderLastActionFeedback(panel, obj.object_id, caseObjectId, opts.lastActionFeedback, opts.detailed);
    renderRecentDialogueHint(panel, state, opts.detailed);
}

function renderKnownState(
    panel: HTMLElement,
    objectState: KvpInvestigationObjectState,
    detailed: boolean
): void {
    if (!detailed) {
        renderSectionTitle(panel, "Known Object State");
        const keyCount = Object.keys(objectState.known_state ?? {}).length;
        renderLines(panel, [["Visible clues", keyCount > 0 ? String(keyCount) : "none yet"]]);
        return;
    }
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
            ? "Action sending is unavailable until the live connection is ready."
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
            ? `Already checked in this run.`
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
    feedback: LastActionFeedback | null,
    detailed: boolean
): void {
    if (!feedback) return;
    const expectedSelectionKey = selectionKeyForObject(worldObjectId, caseObjectId);
    if (feedback.selectionKey !== expectedSelectionKey) return;

    renderSectionTitle(panel, "Latest Result");
    renderLines(panel, detailed
        ? [
            ["Affordance", `${labelMbamAction(feedback.affordanceId)} (${feedback.affordanceId})`],
            ["Status", feedback.result.status],
            ["Code", feedback.result.code],
            ["Tick", String(feedback.tick)],
            ["Summary", feedback.result.summary ?? "none"],
            ["Next step", describeInvestigationFeedback(feedback.result)],
            ["Facts", String(feedback.result.revealed_fact_ids?.length ?? 0)],
            ["Evidence", String(feedback.result.revealed_evidence_ids?.length ?? 0)],
        ]
        : [
            ["Action", labelMbamAction(feedback.affordanceId)],
            ["Result", feedback.result.status],
            ["Summary", feedback.result.summary ?? describeInvestigationFeedback(feedback.result)],
        ]);
}

function renderRecentDialogueHint(panel: HTMLElement, state: WorldState, detailed: boolean): void {
    const dialogue = state.dialogue;
    if (!dialogue || dialogue.recent_turns.length === 0) return;
    const recent = dialogue.recent_turns[dialogue.recent_turns.length - 1] as KvpDialogueTurnLog;
    renderSectionTitle(panel, "Recent Conversation");
    renderLines(panel, detailed
        ? [
            ["Scene", recent.scene_id],
            ["Intent", recent.intent_id],
            ["Result", `${recent.status}/${recent.code}`],
        ]
        : [
            ["Scene", labelSceneFromId(recent.scene_id)],
            ["Result", formatConversationResult(recent.status)],
        ]);
}

function renderObjectPrompt(panel: HTMLElement, caseObjectId: string, state: WorldState): void {
    const onboarding = buildMbamOnboardingView(state);
    const setupGuide = buildMbamCaseSetupGuide(state);
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

    const starterIds = ["O1_DISPLAY_CASE", "O3_WALL_LABEL"];
    const starterComplete = starterIds.every((objectId) => isInvestigationObjectObserved(state, objectId));
    if (!starterComplete) {
        const starterNote = document.createElement("div");
        starterNote.className = "inspect-note";
        starterNote.textContent = starterIds.includes(caseObjectId)
            ? "Priority start object: this is one of your first checks."
            : "For your first pass, inspect the Display Case and Wall Label first.";
        panel.appendChild(starterNote);
    } else if ((state.dialogue?.recent_turns.length ?? 0) === 0) {
        const talkNote = document.createElement("div");
        talkNote.className = "inspect-note";
        talkNote.textContent = `Next step: ${setupGuide.firstTalkTo}`;
        panel.appendChild(talkNote);
    }

    if (state.investigation?.contradictions.required_for_accusation && !state.investigation.contradictions.requirement_satisfied) {
        const contradictionNote = document.createElement("div");
        contradictionNote.className = "inspect-note";
        contradictionNote.textContent =
            "Contradictions matter for accusation. Prioritize timeline-focused object checks.";
        panel.appendChild(contradictionNote);
    }
}

function describeInvestigationFeedback(result: InvestigationActionResult): string {
    if (result.status === "accepted") {
        if (result.code === "projection_affordance_observed") {
            return "Action confirmed. Review new clues and keep following leads.";
        }
        if (result.code === "projection_state_changed") {
            return "Something changed. Cross-check Case Notes and timeline clues.";
        }
        return "Action accepted. Wait for the case view to update.";
    }
    if (result.status === "submitted") {
        return "Action sent. Waiting for update.";
    }
    if (result.status === "unavailable") {
        return "Connection is not ready. Reconnect and try again.";
    }
    if (result.status === "invalid") {
        return "That action is not valid here. Use one of the listed actions.";
    }
    if (result.code === "SCENE_GATE_BLOCKED") {
        return "Blocked for now. Advance the case with more dialogue or clues first.";
    }
    if (result.code === "OBJECT_ACTION_UNAVAILABLE") {
        return "This action is currently blocked. Try another lead.";
    }
    if (result.code === "RUNTIME_NOT_READY") {
        return "Connection is still settling. Wait a moment and retry.";
    }
    return result.summary ?? "Action blocked right now.";
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
    if (!activeObject) return "none";
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
        S1: "Opening interview",
        S2: "Security follow-up",
        S3: "Timeline challenge",
        S4: "Witness check",
        S5: "Final confrontation",
    };
    return labels[sceneId] ?? sceneId;
}

function formatConversationResult(status: string): string {
    if (status.length === 0) return "pending";
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
