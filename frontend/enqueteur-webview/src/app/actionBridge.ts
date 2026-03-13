// src/app/actionBridge.ts
import type { WorldState, WorldStore, KvpDialogueTurnLog } from "../state/worldStore";
import type { InputCommandPayload } from "./live/enqueteurLiveClient";
import type {
    DialogueTurnSubmitRequest,
    DialogueTurnSubmitResult,
} from "../ui/dialoguePanel";
import type {
    InvestigationActionRequest,
    InvestigationActionResult,
} from "../ui/inspectPanel";
import type {
    MinigameSubmitRequest,
    MinigameSubmitResult,
} from "../ui/notebookPanel";
import type {
    AttemptAccusationRequest,
    AttemptRecoveryRequest,
    ResolutionAttemptResult,
} from "../ui/resolutionPanel";
import type { LiveCommandBridge, LiveCommandSubmission } from "./live/liveCommandBridge";
import { resolveRuntimeMessage } from "./runtimeMessage";

type BridgeMode = "live" | "offline";

export type FrontendActionBridgeOpts = {
    store: WorldStore;
    getMode: () => BridgeMode;
    getLiveCommandBridge: () => LiveCommandBridge | null;
    projectionTimeoutMs?: number;
};

export type FrontendActionBridge = {
    canSubmitInvestigationAction: () => boolean;
    canSubmitDialogueTurn: () => boolean;
    canSubmitMinigameSubmit: () => boolean;
    canSubmitResolutionAttempt: () => boolean;
    submitInvestigationAction: (request: InvestigationActionRequest) => Promise<InvestigationActionResult>;
    submitDialogueTurn: (request: DialogueTurnSubmitRequest) => Promise<DialogueTurnSubmitResult>;
    submitMinigameSubmit: (request: MinigameSubmitRequest) => Promise<MinigameSubmitResult>;
    submitAttemptRecovery: (request: AttemptRecoveryRequest) => Promise<ResolutionAttemptResult>;
    submitAttemptAccusation: (request: AttemptAccusationRequest) => Promise<ResolutionAttemptResult>;
};

type LiveInputAvailability = {
    ready: boolean;
    reason: string | null;
};

type InvestigationBaseline = {
    affordanceObserved: boolean;
    objectKnownStateHash: string;
    knownFactIds: Set<string>;
    discoveredEvidenceIds: Set<string>;
    collectedEvidenceIds: Set<string>;
    observedNotCollectedIds: Set<string>;
};

type InvestigationProjectionOutcome = {
    kind: "affordance_observed" | "state_changed";
    newFactIds: string[];
    newEvidenceIds: string[];
};

export function createFrontendActionBridge(opts: FrontendActionBridgeOpts): FrontendActionBridge {
    const projectionTimeoutMs = Math.max(80, Math.floor(opts.projectionTimeoutMs ?? 900));

    const resolveAvailability = (): LiveInputAvailability => {
        if (opts.getMode() !== "live") {
            return {
                ready: false,
                reason: "Action dispatch is disabled in offline/replay mode.",
            };
        }
        const bridge = opts.getLiveCommandBridge();
        if (!bridge || !bridge.canSendInputCommand()) {
            return {
                ready: false,
                reason: "Live runtime connection is not available.",
            };
        }
        return { ready: true, reason: null };
    };

    const submitLiveCommand = async (
        cmd: InputCommandPayload["cmd"]
    ): Promise<LiveCommandSubmission | null> => {
        const availability = resolveAvailability();
        if (!availability.ready) return null;

        const bridge = opts.getLiveCommandBridge();
        if (!bridge) return null;

        return bridge.sendInputCommand(cmd, {
            tickTarget: Math.max(0, opts.store.getState().tick + 1),
        });
    };

    const submitInvestigationAction = async (
        request: InvestigationActionRequest
    ): Promise<InvestigationActionResult> => {
        const availability = resolveAvailability();
        if (!availability.ready) {
            return {
                status: "unavailable",
                code: "live_dispatch_unavailable",
                summary: availability.reason ?? "Action dispatch unavailable.",
            };
        }

        const baseline = captureInvestigationBaseline(opts.store.getState(), request);
        const commandResult = await submitLiveCommand({
            type: "INVESTIGATE_OBJECT",
            payload: {
                object_id: request.caseObjectId,
                action_id: request.affordanceId,
            },
        });
        if (!commandResult) {
            return {
                status: "unavailable",
                code: "command_send_unavailable",
                summary: "Live runtime connection is not available.",
            };
        }
        if (!commandResult.accepted) {
            return {
                status: mapCommandRejectionToInvestigativeStatus(commandResult.reasonCode),
                code: commandResult.reasonCode ?? "COMMAND_REJECTED",
                summary: formatCommandRejectionSummary(commandResult),
            };
        }

        const projected = await waitForInvestigationProjectionOutcome(
            opts.store,
            request,
            baseline,
            projectionTimeoutMs
        );
        if (!projected) {
            return {
                status: "submitted",
                code: "awaiting_projection_update",
                summary: "Command accepted; waiting for projected investigation update.",
            };
        }
        if (projected.kind === "affordance_observed") {
            return {
                status: "accepted",
                code: "projection_affordance_observed",
                summary: "Projected state confirms this affordance was observed.",
                revealed_fact_ids: projected.newFactIds,
                revealed_evidence_ids: projected.newEvidenceIds,
            };
        }
        return {
            status: "accepted",
            code: "projection_state_changed",
            summary: "Projected investigation state changed after submission.",
            revealed_fact_ids: projected.newFactIds,
            revealed_evidence_ids: projected.newEvidenceIds,
        };
    };

    const submitDialogueTurn = async (
        request: DialogueTurnSubmitRequest
    ): Promise<DialogueTurnSubmitResult> => {
        const availability = resolveAvailability();
        if (!availability.ready) {
            return {
                status: "unavailable",
                code: "live_dispatch_unavailable",
                summary: availability.reason ?? "Dialogue dispatch unavailable.",
            };
        }

        const slots: Record<string, unknown> = {};
        for (const slot of request.providedSlots) {
            slots[slot.slot_name] = slot.value;
        }

        const baselineTurnCount = opts.store.getState().dialogue?.recent_turns.length ?? 0;
        const commandResult = await submitLiveCommand({
            type: "DIALOGUE_TURN",
            payload: {
                scene_id: request.sceneId,
                npc_id: request.npcId,
                intent_id: request.intentId,
                slots,
            },
        });
        if (!commandResult) {
            return {
                status: "unavailable",
                code: "command_send_unavailable",
                summary: "Live runtime connection is not available.",
            };
        }
        if (!commandResult.accepted) {
            return {
                status: mapCommandRejectionToDialogueStatus(commandResult.reasonCode),
                code: commandResult.reasonCode ?? "COMMAND_REJECTED",
                summary: formatCommandRejectionSummary(commandResult),
            };
        }

        const projectedTurn = await waitForDialogueProjectedTurn(
            opts.store,
            request,
            baselineTurnCount,
            projectionTimeoutMs
        );
        if (!projectedTurn) {
            return {
                status: "submitted",
                code: "awaiting_projection_update",
                summary: "Turn accepted; waiting for projected dialogue update.",
            };
        }
        return {
            status: mapDialogueTurnStatus(projectedTurn.status),
            code: projectedTurn.code,
            summary: `${projectedTurn.outcome} (${projectedTurn.response_mode})`,
            revealed_fact_ids: [...projectedTurn.revealed_fact_ids],
        };
    };

    const submitMinigameSubmit = async (
        request: MinigameSubmitRequest
    ): Promise<MinigameSubmitResult> => {
        const availability = resolveAvailability();
        if (!availability.ready) {
            return {
                status: "unavailable",
                code: "live_dispatch_unavailable",
                summary: availability.reason ?? "Minigame dispatch unavailable.",
            };
        }

        const commandResult = await submitLiveCommand({
            type: "MINIGAME_SUBMIT",
            payload: {
                minigame_id: request.minigameId,
                target_id: request.targetId,
                answer: request.answer,
            },
        });
        if (!commandResult) {
            return {
                status: "unavailable",
                code: "command_send_unavailable",
                summary: "Live runtime connection is not available.",
            };
        }
        if (!commandResult.accepted) {
            return {
                status: mapCommandRejectionToGenericStatus(commandResult.reasonCode),
                code: commandResult.reasonCode ?? "COMMAND_REJECTED",
                summary: formatCommandRejectionSummary(commandResult),
            };
        }
        return {
            status: "submitted",
            code: "command_accepted_waiting_projection",
            summary: "Minigame submission accepted; waiting for authoritative diff update.",
        };
    };

    const submitAttemptRecovery = async (
        request: AttemptRecoveryRequest
    ): Promise<ResolutionAttemptResult> => {
        const availability = resolveAvailability();
        if (!availability.ready) {
            return {
                status: "unavailable",
                code: "live_dispatch_unavailable",
                summary: availability.reason ?? "Recovery dispatch unavailable.",
            };
        }

        const commandResult = await submitLiveCommand({
            type: "ATTEMPT_RECOVERY",
            payload: {
                target_id: request.targetId,
            },
        });
        if (!commandResult) {
            return {
                status: "unavailable",
                code: "command_send_unavailable",
                summary: "Live runtime connection is not available.",
            };
        }
        if (!commandResult.accepted) {
            return {
                status: mapCommandRejectionToGenericStatus(commandResult.reasonCode),
                code: commandResult.reasonCode ?? "COMMAND_REJECTED",
                summary: formatCommandRejectionSummary(commandResult),
            };
        }
        return {
            status: "submitted",
            code: "command_accepted_waiting_projection",
            summary: "Recovery attempt accepted; waiting for authoritative diff update.",
        };
    };

    const submitAttemptAccusation = async (
        request: AttemptAccusationRequest
    ): Promise<ResolutionAttemptResult> => {
        const availability = resolveAvailability();
        if (!availability.ready) {
            return {
                status: "unavailable",
                code: "live_dispatch_unavailable",
                summary: availability.reason ?? "Accusation dispatch unavailable.",
            };
        }

        const commandResult = await submitLiveCommand({
            type: "ATTEMPT_ACCUSATION",
            payload: {
                suspect_id: request.suspectId,
                supporting_fact_ids: request.supportingFactIds,
                supporting_evidence_ids: request.supportingEvidenceIds,
            },
        });
        if (!commandResult) {
            return {
                status: "unavailable",
                code: "command_send_unavailable",
                summary: "Live runtime connection is not available.",
            };
        }
        if (!commandResult.accepted) {
            return {
                status: mapCommandRejectionToGenericStatus(commandResult.reasonCode),
                code: commandResult.reasonCode ?? "COMMAND_REJECTED",
                summary: formatCommandRejectionSummary(commandResult),
            };
        }
        return {
            status: "submitted",
            code: "command_accepted_waiting_projection",
            summary: "Accusation attempt accepted; waiting for authoritative diff update.",
        };
    };

    return {
        canSubmitInvestigationAction: () => resolveAvailability().ready,
        canSubmitDialogueTurn: () => resolveAvailability().ready,
        canSubmitMinigameSubmit: () => resolveAvailability().ready,
        canSubmitResolutionAttempt: () => resolveAvailability().ready,
        submitInvestigationAction,
        submitDialogueTurn,
        submitMinigameSubmit,
        submitAttemptRecovery,
        submitAttemptAccusation,
    };
}

function mapCommandRejectionToInvestigativeStatus(reasonCode?: string): InvestigationActionResult["status"] {
    if (!reasonCode) return "invalid";
    if (reasonCode === "OBJECT_ACTION_UNAVAILABLE") return "blocked";
    if (reasonCode === "RUNTIME_NOT_READY") return "unavailable";
    if (reasonCode.startsWith("INVALID")) return "invalid";
    return "blocked";
}

function mapCommandRejectionToDialogueStatus(reasonCode?: string): DialogueTurnSubmitResult["status"] {
    if (!reasonCode) return "invalid";
    if (reasonCode === "MISSING_REQUIRED_SLOTS") return "invalid";
    if (reasonCode === "INVALID_NPC") return "invalid";
    if (reasonCode === "INSUFFICIENT_TRUST") return "blocked";
    if (reasonCode === "SCENE_GATE_BLOCKED") return "blocked";
    if (reasonCode === "RUNTIME_NOT_READY") return "unavailable";
    if (reasonCode.startsWith("INVALID")) return "invalid";
    return "blocked";
}

function mapCommandRejectionToGenericStatus(reasonCode?: string): "blocked" | "invalid" | "unavailable" {
    if (!reasonCode) return "invalid";
    if (reasonCode === "RUNTIME_NOT_READY") return "unavailable";
    if (reasonCode.startsWith("INVALID")) return "invalid";
    return "blocked";
}

function formatCommandRejectionSummary(result: LiveCommandSubmission): string {
    const resolved = resolveRuntimeMessage({
        message: result.message,
        messageKey: result.messageKey,
        messageParams: result.messageParams,
    });
    if (resolved.trim().length > 0) return resolved;
    return "That action is blocked by the current case state.";
}

function captureInvestigationBaseline(
    state: WorldState,
    request: InvestigationActionRequest
): InvestigationBaseline {
    const objectRow = state.investigation?.objects.find((row) => row.object_id === request.caseObjectId) ?? null;
    const affordanceObserved = objectRow?.observed_affordances.includes(request.affordanceId) ?? false;
    const objectKnownStateHash = stableHashJson(objectRow?.known_state ?? {});
    return {
        affordanceObserved,
        objectKnownStateHash,
        knownFactIds: new Set(state.investigation?.facts.known_fact_ids ?? []),
        discoveredEvidenceIds: new Set(state.investigation?.evidence.discovered_ids ?? []),
        collectedEvidenceIds: new Set(state.investigation?.evidence.collected_ids ?? []),
        observedNotCollectedIds: new Set(state.investigation?.evidence.observed_not_collected_ids ?? []),
    };
}

function detectInvestigationProjectionOutcome(
    state: WorldState,
    request: InvestigationActionRequest,
    baseline: InvestigationBaseline
): InvestigationProjectionOutcome | null {
    const investigation = state.investigation;
    if (!investigation) return null;

    const objectRow = investigation.objects.find((row) => row.object_id === request.caseObjectId) ?? null;
    const affordanceObserved = objectRow?.observed_affordances.includes(request.affordanceId) ?? false;
    const objectKnownStateHash = stableHashJson(objectRow?.known_state ?? {});

    const newFactIds = toSortedDiff(investigation.facts.known_fact_ids, baseline.knownFactIds);
    const newEvidenceIds = toSortedDiff(investigation.evidence.discovered_ids, baseline.discoveredEvidenceIds);
    const newCollectedIds = toSortedDiff(investigation.evidence.collected_ids, baseline.collectedEvidenceIds);
    const newObservedNotCollected = toSortedDiff(
        investigation.evidence.observed_not_collected_ids,
        baseline.observedNotCollectedIds
    );
    const mergedEvidence = Array.from(new Set([...newEvidenceIds, ...newCollectedIds])).sort();

    if (!baseline.affordanceObserved && affordanceObserved) {
        return {
            kind: "affordance_observed",
            newFactIds,
            newEvidenceIds: mergedEvidence,
        };
    }

    const stateChanged =
        newFactIds.length > 0 ||
        mergedEvidence.length > 0 ||
        newObservedNotCollected.length > 0 ||
        objectKnownStateHash !== baseline.objectKnownStateHash;
    if (stateChanged) {
        return {
            kind: "state_changed",
            newFactIds,
            newEvidenceIds: mergedEvidence,
        };
    }
    return null;
}

function waitForInvestigationProjectionOutcome(
    store: WorldStore,
    request: InvestigationActionRequest,
    baseline: InvestigationBaseline,
    timeoutMs: number
): Promise<InvestigationProjectionOutcome | null> {
    return waitForStoreProjectionResult(
        store,
        (state) => detectInvestigationProjectionOutcome(state, request, baseline),
        timeoutMs
    );
}

function waitForDialogueProjectedTurn(
    store: WorldStore,
    request: DialogueTurnSubmitRequest,
    baselineTurnCount: number,
    timeoutMs: number
): Promise<KvpDialogueTurnLog | null> {
    return waitForStoreProjectionResult(store, (state) => {
        const dialogue = state.dialogue;
        if (!dialogue) return null;
        if (dialogue.recent_turns.length <= baselineTurnCount) return null;
        const candidates = dialogue.recent_turns.slice(baselineTurnCount);

        for (let i = candidates.length - 1; i >= 0; i -= 1) {
            const row = candidates[i];
            if (
                row.scene_id === request.sceneId &&
                row.npc_id === request.npcId &&
                row.intent_id === request.intentId
            ) {
                return row;
            }
        }
        return null;
    }, timeoutMs);
}

function waitForStoreProjectionResult<TResult>(
    store: WorldStore,
    evaluator: (state: WorldState) => TResult | null,
    timeoutMs: number
): Promise<TResult | null> {
    return new Promise((resolve) => {
        let settled = false;
        let needsUnsubAfterAttach = false;
        let unsub: (() => void) | null = null;
        let timer = 0;
        const finish = (value: TResult | null): void => {
            if (settled) return;
            settled = true;
            if (unsub) {
                unsub();
                unsub = null;
            } else {
                needsUnsubAfterAttach = true;
            }
            window.clearTimeout(timer);
            resolve(value);
        };
        const attachedUnsub = store.subscribe((state) => {
            const outcome = evaluator(state);
            if (outcome !== null) finish(outcome);
        });
        if (needsUnsubAfterAttach) {
            attachedUnsub();
            unsub = null;
        } else {
            unsub = attachedUnsub;
        }
        timer = window.setTimeout(() => finish(null), timeoutMs);
    });
}

function mapDialogueTurnStatus(status: string): DialogueTurnSubmitResult["status"] {
    if (status === "accepted") return "accepted";
    if (status === "repair") return "repair";
    if (status === "refused") return "refused";
    if (status.startsWith("invalid")) return "invalid";
    if (status.startsWith("blocked")) return "blocked";
    return "submitted";
}

function toSortedDiff(values: string[], baseline: Set<string>): string[] {
    return values.filter((row) => !baseline.has(row)).sort();
}

function stableHashJson(value: unknown): string {
    return stableStringify(value);
}

function stableStringify(value: unknown): string {
    if (Array.isArray(value)) {
        return `[${value.map((item) => stableStringify(item)).join(",")}]`;
    }
    if (value && typeof value === "object") {
        const row = value as Record<string, unknown>;
        const keys = Object.keys(row).sort();
        const entries = keys.map((key) => `${JSON.stringify(key)}:${stableStringify(row[key])}`);
        return `{${entries.join(",")}}`;
    }
    return JSON.stringify(value) ?? "undefined";
}
