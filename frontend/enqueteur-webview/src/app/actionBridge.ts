// src/app/actionBridge.ts
import type { KvpClient } from "../kvp/client";
import type { KvpDialogueTurnLog, WorldState, WorldStore } from "../state/worldStore";
import type {
    DialogueTurnSubmitRequest,
    DialogueTurnSubmitResult,
} from "../ui/dialoguePanel";
import type {
    InvestigationActionRequest,
    InvestigationActionResult,
} from "../ui/inspectPanel";

type BridgeMode = "live" | "offline";

export type FrontendActionBridgeOpts = {
    store: WorldStore;
    getMode: () => BridgeMode;
    getClient: () => KvpClient | null;
    projectionTimeoutMs?: number;
};

export type FrontendActionBridge = {
    canSubmitInvestigationAction: () => boolean;
    canSubmitDialogueTurn: () => boolean;
    submitInvestigationAction: (request: InvestigationActionRequest) => Promise<InvestigationActionResult>;
    submitDialogueTurn: (request: DialogueTurnSubmitRequest) => Promise<DialogueTurnSubmitResult>;
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
        const client = opts.getClient();
        if (!client || !client.canSendSimInput()) {
            return {
                ready: false,
                reason: "Live runtime connection is not available.",
            };
        }
        return { ready: true, reason: null };
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
        const client = opts.getClient();
        if (!client || !client.sendSimInput({
            type: "MBAM_INVESTIGATION_COMMAND",
            object_id: request.caseObjectId,
            affordance_id: request.affordanceId,
            world_object_id: request.worldObjectId,
            tick: request.tick,
        })) {
            return {
                status: "unavailable",
                code: "sim_input_not_sent",
                summary: "Live runtime connection is not available.",
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
                summary: "Command submitted; waiting for projected investigation update.",
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

        const baselineTurnCount = opts.store.getState().dialogue?.recent_turns.length ?? 0;
        const client = opts.getClient();
        if (!client || !client.sendSimInput({
            type: "MBAM_DIALOGUE_TURN",
            scene_id: request.sceneId,
            npc_id: request.npcId,
            intent_id: request.intentId,
            provided_slots: request.providedSlots,
            presented_fact_ids: request.presentedFactIds,
            presented_evidence_ids: request.presentedEvidenceIds,
            utterance_text: request.utteranceText ?? null,
            tick: request.tick,
        })) {
            return {
                status: "unavailable",
                code: "sim_input_not_sent",
                summary: "Live runtime connection is not available.",
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
                summary: "Turn submitted; waiting for projected dialogue update.",
            };
        }
        return {
            status: mapDialogueTurnStatus(projectedTurn.status),
            code: projectedTurn.code,
            summary: `${projectedTurn.outcome} (${projectedTurn.response_mode})`,
            revealed_fact_ids: [...projectedTurn.revealed_fact_ids],
        };
    };

    return {
        canSubmitInvestigationAction: () => resolveAvailability().ready,
        canSubmitDialogueTurn: () => resolveAvailability().ready,
        submitInvestigationAction,
        submitDialogueTurn,
    };
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
        return candidates[candidates.length - 1] ?? null;
    }, timeoutMs);
}

function waitForStoreProjectionResult<TResult>(
    store: WorldStore,
    evaluator: (state: WorldState) => TResult | null,
    timeoutMs: number
): Promise<TResult | null> {
    return new Promise((resolve) => {
        let settled = false;
        let unsub: () => void = () => {};
        let timer = 0;
        const finish = (value: TResult | null): void => {
            if (settled) return;
            settled = true;
            unsub();
            window.clearTimeout(timer);
            resolve(value);
        };
        unsub = store.subscribe((state) => {
            const outcome = evaluator(state);
            if (outcome !== null) finish(outcome);
        });
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
