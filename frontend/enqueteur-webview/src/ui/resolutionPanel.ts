import type { WorldState, WorldStore } from "../state/worldStore";

export type ResolutionPanelHandle = {
    root: HTMLElement;
    setPresentationProfile?: (profile: "demo" | "playtest" | "dev") => void;
};

export type AttemptRecoveryRequest = {
    targetId: string;
    tick: number;
};

export type AttemptAccusationRequest = {
    suspectId: string;
    supportingFactIds: string[];
    supportingEvidenceIds: string[];
    tick: number;
};

export type ResolutionAttemptResult = {
    status: "submitted" | "accepted" | "blocked" | "invalid" | "unavailable" | "error";
    code: string;
    summary?: string;
};

export type ResolutionPanelOpts = {
    dispatchAttemptRecovery?: (
        request: AttemptRecoveryRequest
    ) => Promise<ResolutionAttemptResult> | ResolutionAttemptResult;
    dispatchAttemptAccusation?: (
        request: AttemptAccusationRequest
    ) => Promise<ResolutionAttemptResult> | ResolutionAttemptResult;
    canDispatchResolutionAttempt?: () => boolean;
    presentationProfile?: "demo" | "playtest" | "dev";
};

const FACT_LABELS: Record<string, string> = {
    N1: "N1 Missing item discovered",
    N2: "N2 Corridor badge access",
    N3: "N3 Badge log 17h58",
    N4: "N4 Cafe receipt 17h52",
    N5: "N5 Witness clothing",
    N6: "N6 Torn note clue",
    N7: "N7 Vitrine latch clue",
    N8: "N8 Drop location clue",
};

const EVIDENCE_LABELS: Record<string, string> = {
    E1_TORN_NOTE: "E1 Torn Note",
    E2_CAFE_RECEIPT: "E2 Cafe Receipt",
    E3_METHOD_TRACE: "E3 Method Trace",
};

const SUSPECT_LABELS: Record<string, string> = {
    laurent: "Laurent",
    samira: "Samira",
    outsider: "Outside Actor",
};

type AttemptReadinessState = "available" | "risky" | "blocked";

type AttemptReadiness = {
    state: AttemptReadinessState;
    reason: string;
};

type ResolutionReadiness = {
    terminal: boolean;
    contradictionRequired: boolean;
    contradictionSatisfied: boolean;
    supportFactCount: number;
    supportEvidenceCount: number;
    recovery: AttemptReadiness;
    accusation: AttemptReadiness;
};

export function mountResolutionPanel(store: WorldStore, opts: ResolutionPanelOpts = {}): ResolutionPanelHandle {
    const root = document.createElement("div");
    root.className = "resolution-root";

    const panel = document.createElement("div");
    panel.className = "resolution-panel";
    root.appendChild(panel);

    let lastState: WorldState | null = null;
    let selectedSuspectId = "laurent";
    let lastActionMessage: string | null = null;
    let pendingAction = false;
    let presentationProfile: "demo" | "playtest" | "dev" = opts.presentationProfile ?? "playtest";

    const render = (): void => {
        panel.innerHTML = "";
        if (!lastState) {
            panel.style.display = "none";
            return;
        }
        panel.style.display = "block";

        const title = document.createElement("div");
        title.className = "resolution-title";
        title.textContent = "Final Decision";
        panel.appendChild(title);

        const recap = lastState.caseRecap;
        const outcome = lastState.caseOutcome;
        const detailed = presentationProfile !== "demo";
        const dispatchAllowed = canDispatch();
        const readiness = buildResolutionReadiness(lastState, recap, outcome, {
            canDispatch: dispatchAllowed,
            hasRecoveryDispatcher: Boolean(opts.dispatchAttemptRecovery),
            hasAccusationDispatcher: Boolean(opts.dispatchAttemptAccusation),
        });
        if (!recap && !outcome) {
            renderInfo(panel, "Final report is not available yet.");
            renderResolutionActions(panel, readiness, detailed);
            return;
        }

        const truthEpoch = recap?.truth_epoch ?? outcome?.truth_epoch ?? 1;
        const finalOutcome = recap?.final_outcome_type ?? outcome?.primary_outcome ?? "in_progress";
        const path = recap?.resolution_path ?? fallbackPathFromOutcome(outcome?.primary_outcome);
        const available = recap?.available ?? Boolean(outcome?.terminal);
        const contradictionUsed = recap?.contradiction_used ?? false;
        const contradictionSatisfied = recap?.contradiction_requirement_satisfied ?? (outcome?.contradiction_requirement_satisfied ?? false);
        const bestAwarded = recap?.best_outcome.awarded ?? (outcome?.best_outcome_awarded ?? false);

        renderLines(panel, detailed
            ? [
                ["Case state", `v${truthEpoch}`],
                ["Outcome", finalOutcome],
                ["Resolution path", path],
                ["Status", available ? "resolved" : "in progress"],
                ["Contradiction", contradictionUsed ? "used" : (contradictionSatisfied ? "satisfied" : "pending")],
                ["Best outcome", bestAwarded ? "earned" : "not earned"],
            ]
            : [
                ["Outcome", finalOutcome],
                ["Path", path],
                ["Status", available ? "resolved" : "in progress"],
            ]);
        renderInfo(panel, summarizeOutcome(finalOutcome, path, recap?.soft_fail.triggered ?? false, bestAwarded));
        renderSectionTitle(panel, "Decision Readiness");
        renderLines(panel, [
            ["Recovery", `${readiness.recovery.state} - ${readiness.recovery.reason}`],
            ["Accusation", `${readiness.accusation.state} - ${readiness.accusation.reason}`],
            ["Support", `${readiness.supportFactCount} facts / ${readiness.supportEvidenceCount} evidence`],
            ["Contradiction", readiness.contradictionRequired ? (readiness.contradictionSatisfied ? "ready" : "pending") : "not required"],
        ]);
        renderResolutionActions(panel, readiness, detailed);

        if (!recap) {
            return;
        }
        if (!recap.available) {
            renderInfo(panel, "The full recap appears once the case reaches an ending.");
            return;
        }

        renderSection(panel, "Why This Ending", buildOutcomeWhyRows(recap, outcome));
        renderSection(panel, "Key Facts", recap.key_fact_ids.map((factId) => FACT_LABELS[factId] ?? factId));
        renderSection(panel, "Key Evidence", recap.key_evidence_ids.map((evidenceId) => EVIDENCE_LABELS[evidenceId] ?? evidenceId));
        renderSection(panel, "Path Highlights", [
            ...recap.key_action_flags.map((flag) => formatActionFlag(flag, detailed)),
            ...recap.contradiction_action_flags.map((flag) => formatActionFlag(flag, detailed)),
        ]);
        renderSection(panel, "Aftermath", [
            ...recap.relationship_result_flags.map((flag) => formatOutcomeFlag(flag, detailed)),
            ...recap.continuity_flags.map((flag) => formatOutcomeFlag(flag, detailed)),
        ]);

        const markers: string[] = [];
        if (recap.best_outcome.awarded) markers.push("best_outcome_awarded");
        if (recap.best_outcome.quiet_recovery) markers.push("quiet_recovery");
        if (recap.best_outcome.no_public_escalation) markers.push("no_public_escalation");
        if (recap.best_outcome.strong_key_trust) markers.push("strong_key_trust");
        if (markers.length > 0) {
        renderSection(panel, "Best Outcome Markers", markers.map((marker) => formatBestOutcomeMarker(marker, detailed)));
        }
        if (recap.soft_fail.triggered) {
            renderSection(panel, "Setback Triggers", recap.soft_fail.trigger_conditions.map((trigger) => formatSoftFailTrigger(trigger, detailed)));
        }
    };

    const canDispatch = (): boolean => {
        if (!opts.canDispatchResolutionAttempt) {
            return Boolean(opts.dispatchAttemptRecovery || opts.dispatchAttemptAccusation);
        }
        return opts.canDispatchResolutionAttempt();
    };

    const renderResolutionActions = (
        panelEl: HTMLElement,
        readiness: ResolutionReadiness,
        detailed: boolean
    ): void => {
        renderSectionTitle(panelEl, "Final Actions");

        const info = document.createElement("div");
        info.className = "resolution-info";
        info.textContent = readiness.terminal
            ? "This case is already closed. Review the recap to see what mattered."
            : "Use Recovery or Accusation when your support is strong enough.";
        panelEl.appendChild(info);

        if (lastActionMessage) {
            const feedback = document.createElement("div");
            feedback.className = "resolution-info";
            feedback.textContent = lastActionMessage;
            panelEl.appendChild(feedback);
        }

        const row = document.createElement("div");
        row.className = "flow-actions";

        const recoveryBtn = document.createElement("button");
        recoveryBtn.type = "button";
        recoveryBtn.className = "flow-action-btn";
        recoveryBtn.textContent = pendingAction ? "Sending..." : "Attempt Recovery";
        recoveryBtn.disabled = pendingAction || readiness.recovery.state === "blocked";
        recoveryBtn.addEventListener("click", () => {
            if (!lastState || !opts.dispatchAttemptRecovery) return;
            pendingAction = true;
            lastActionMessage = "Sending recovery attempt...";
            render();
            void Promise.resolve(
                opts.dispatchAttemptRecovery({
                    targetId: "O2_MEDALLION",
                    tick: lastState.tick,
                })
            ).then((result) => {
                pendingAction = false;
                lastActionMessage = formatAttemptResult("recovery", result, detailed);
                render();
            }).catch((err: unknown) => {
                pendingAction = false;
                const message = err instanceof Error ? err.message : String(err);
                lastActionMessage = `Could not send recovery attempt: ${message}`;
                render();
            });
        });
        row.appendChild(recoveryBtn);

        const suspect = document.createElement("select");
        suspect.className = "flow-action-btn";
        for (const suspectId of ["laurent", "samira", "outsider"]) {
            const option = document.createElement("option");
            option.value = suspectId;
            option.textContent = SUSPECT_LABELS[suspectId] ?? suspectId;
            option.selected = suspectId === selectedSuspectId;
            suspect.appendChild(option);
        }
        suspect.disabled = pendingAction || readiness.accusation.state === "blocked";
        suspect.addEventListener("change", () => {
            selectedSuspectId = suspect.value;
        });
        row.appendChild(suspect);

        const accusationBtn = document.createElement("button");
        accusationBtn.type = "button";
        accusationBtn.className = "flow-action-btn";
        accusationBtn.textContent = pendingAction ? "Sending..." : "Attempt Accusation";
        accusationBtn.disabled = pendingAction || readiness.accusation.state === "blocked";
        accusationBtn.addEventListener("click", () => {
            if (!lastState || !opts.dispatchAttemptAccusation) return;
            pendingAction = true;
            lastActionMessage = "Sending accusation attempt...";
            render();
            const facts = lastState.investigation?.facts.known_fact_ids ?? [];
            const evidence = Array.from(new Set([
                ...(lastState.investigation?.evidence.discovered_ids ?? []),
                ...(lastState.investigation?.evidence.collected_ids ?? []),
            ]));
            void Promise.resolve(
                opts.dispatchAttemptAccusation({
                    suspectId: selectedSuspectId,
                    supportingFactIds: [...facts],
                    supportingEvidenceIds: [...evidence],
                    tick: lastState.tick,
                })
            ).then((result) => {
                pendingAction = false;
                lastActionMessage = formatAttemptResult("accusation", result, detailed);
                render();
            }).catch((err: unknown) => {
                pendingAction = false;
                const message = err instanceof Error ? err.message : String(err);
                lastActionMessage = `Could not send accusation attempt: ${message}`;
                render();
            });
        });
        row.appendChild(accusationBtn);

        panelEl.appendChild(row);
        renderInfo(panelEl, `Recovery: ${readiness.recovery.state} (${readiness.recovery.reason})`);
        renderInfo(panelEl, `Accusation: ${readiness.accusation.state} (${readiness.accusation.reason})`);
    };

    const unsub = store.subscribe((state) => {
        lastState = state;
        render();
    });
    root.addEventListener("DOMNodeRemoved", () => unsub(), { once: true });

    return {
        root,
        setPresentationProfile: (profile) => {
            presentationProfile = profile;
            render();
        },
    };
}

function fallbackPathFromOutcome(outcome: string | undefined): string {
    if (outcome === "soft_fail") return "soft_fail";
    if (outcome === "recovery_success") return "recovery";
    if (outcome === "accusation_success") return "accusation";
    if (outcome === "best_outcome") return "recovery";
    return "in_progress";
}

function buildResolutionReadiness(
    state: WorldState,
    recap: WorldState["caseRecap"],
    outcome: WorldState["caseOutcome"],
    opts: {
        canDispatch: boolean;
        hasRecoveryDispatcher: boolean;
        hasAccusationDispatcher: boolean;
    }
): ResolutionReadiness {
    const terminal = recap?.available ?? Boolean(outcome?.terminal);
    const knownFacts = state.investigation?.facts.known_fact_ids ?? [];
    const knownEvidence = Array.from(
        new Set([
            ...(state.investigation?.evidence.discovered_ids ?? []),
            ...(state.investigation?.evidence.collected_ids ?? []),
        ])
    );
    const contradictionRequired =
        state.investigation?.contradictions.required_for_accusation
        ?? outcome?.contradiction_required_for_accusation
        ?? false;
    const contradictionSatisfied =
        state.investigation?.contradictions.requirement_satisfied
        ?? recap?.contradiction_requirement_satisfied
        ?? outcome?.contradiction_requirement_satisfied
        ?? false;

    const baseBlockedReason = terminal
        ? "case already closed"
        : !opts.canDispatch
          ? "connection is not ready"
          : "";

    const recovery: AttemptReadiness = (() => {
        if (baseBlockedReason.length > 0) return { state: "blocked", reason: baseBlockedReason };
        if (!opts.hasRecoveryDispatcher) return { state: "blocked", reason: "recovery action unavailable" };
        if (knownFacts.length < 2 || knownEvidence.length < 1) {
            return { state: "risky", reason: "support is thin; outcome may be weaker" };
        }
        return { state: "available", reason: "support is strong enough to proceed" };
    })();

    const accusation: AttemptReadiness = (() => {
        if (baseBlockedReason.length > 0) return { state: "blocked", reason: baseBlockedReason };
        if (!opts.hasAccusationDispatcher) return { state: "blocked", reason: "accusation action unavailable" };
        if (contradictionRequired && !contradictionSatisfied) {
            return { state: "blocked", reason: "contradiction requirement not met yet" };
        }
        if (knownFacts.length < 3 || knownEvidence.length < 1) {
            return { state: "risky", reason: "supporting clues are still thin" };
        }
        return { state: "available", reason: "requirements appear ready" };
    })();

    return {
        terminal,
        contradictionRequired,
        contradictionSatisfied,
        supportFactCount: knownFacts.length,
        supportEvidenceCount: knownEvidence.length,
        recovery,
        accusation,
    };
}

function summarizeOutcome(
    outcomeType: string,
    path: string,
    softFailTriggered: boolean,
    bestAwarded: boolean
): string {
    if (outcomeType === "best_outcome" || bestAwarded) {
        return "Best outcome achieved: the case closed with strong corroboration and minimal fallout.";
    }
    if (outcomeType === "recovery_success") {
        return "Recovery path completed: the missing item was recovered without full accusation escalation.";
    }
    if (outcomeType === "accusation_success") {
        return "Accusation path completed: the case closed through suspect attribution.";
    }
    if (outcomeType === "soft_fail" || softFailTriggered) {
        return "Soft-fail outcome: the case ended with unresolved costs or missed safeguards.";
    }
    if (path === "in_progress") {
        return "Case is in progress. Continue collecting corroborated facts and evidence before final attempts.";
    }
    return "Resolution state updated. Review path highlights below.";
}

function buildOutcomeWhyRows(
    recap: NonNullable<WorldState["caseRecap"]>,
    outcome: WorldState["caseOutcome"]
): string[] {
    const rows: string[] = [];
    rows.push(`Path completed: ${recap.resolution_path}`);
    rows.push(`Key facts considered: ${recap.key_fact_ids.length}`);
    rows.push(`Key evidence considered: ${recap.key_evidence_ids.length}`);
    rows.push(
        recap.contradiction_requirement_satisfied
            ? "Contradiction requirement: satisfied"
            : "Contradiction requirement: still pending when outcome resolved"
    );
    if (recap.contradiction_used) {
        rows.push("Contradiction use: applied in final path");
    }
    if (recap.soft_fail.triggered) {
        rows.push("Soft-fail pressure influenced the final result.");
    }
    if (outcome?.public_escalation) {
        rows.push("Public escalation occurred during resolution.");
    }
    return rows;
}

function formatActionFlag(flag: string, detailed: boolean): string {
    const known: Record<string, string> = {
        "action:recover_medallion": "Recovered medallion action path",
        "action:accuse_samira": "Accusation centered on Samira",
        "action:state_contradiction_N3_N4": "Contradiction between badge log and receipt timing",
    };
    if (known[flag]) return detailed ? `${known[flag]} (${flag})` : known[flag];
    return detailed ? `${humanizeToken(flag)} (${flag})` : humanizeToken(flag);
}

function formatOutcomeFlag(flag: string, detailed: boolean): string {
    const known: Record<string, string> = {
        "continuity:quiet_recovery": "Quiet recovery maintained",
        "continuity:strong_key_trust": "Key trust remained strong",
        rel_elodie_positive: "Elodie relationship ended positive",
        rel_marc_positive: "Marc relationship ended positive",
    };
    if (known[flag]) return detailed ? `${known[flag]} (${flag})` : known[flag];
    return detailed ? `${humanizeToken(flag)} (${flag})` : humanizeToken(flag);
}

function formatSoftFailTrigger(trigger: string, detailed: boolean): string {
    const known: Record<string, string> = {
        item_left_building: "Item left the building before secure recovery",
        public_escalation: "Public escalation escalated case pressure",
    };
    if (known[trigger]) return detailed ? `${known[trigger]} (${trigger})` : known[trigger];
    return detailed ? `${humanizeToken(trigger)} (${trigger})` : humanizeToken(trigger);
}

function formatBestOutcomeMarker(marker: string, detailed: boolean): string {
    const known: Record<string, string> = {
        best_outcome_awarded: "Best outcome awarded",
        quiet_recovery: "Quiet recovery preserved",
        no_public_escalation: "No public escalation",
        strong_key_trust: "Strong key trust maintained",
    };
    if (known[marker]) return detailed ? `${known[marker]} (${marker})` : known[marker];
    return detailed ? `${humanizeToken(marker)} (${marker})` : humanizeToken(marker);
}

function formatAttemptResult(
    kind: "recovery" | "accusation",
    result: ResolutionAttemptResult,
    detailed: boolean
): string {
    const title = kind === "recovery" ? "Recovery" : "Accusation";
    if (result.status === "accepted" || result.status === "submitted") {
        return detailed
            ? `${title} sent. Waiting for case outcome update. [${result.code}]`
            : `${title} sent. Waiting for outcome update.`;
    }
    if (result.status === "blocked") {
        const reason = mapAttemptReasonCode(result.code, result.summary);
        return detailed
            ? `${title} blocked: ${reason} [${result.code}]`
            : `${title} blocked: ${reason}.`;
    }
    if (result.status === "invalid") {
        return detailed
            ? `${title} invalid: details or prerequisites do not match. [${result.code}]`
            : `${title} invalid: details or prerequisites do not match.`;
    }
    if (result.status === "unavailable") {
        return detailed
            ? `${title} unavailable: connection not ready. [${result.code}]`
            : `${title} unavailable: connection not ready.`;
    }
    if (result.status === "error") {
        return detailed
            ? `${title} send error: ${result.summary ?? "unknown error"} [${result.code}]`
            : `${title} send error: ${result.summary ?? "unknown error"}`;
    }
    return detailed
        ? `${title}: ${result.summary ?? "Command processed."} [${result.code}]`
        : `${title}: ${result.summary ?? "Command processed."}`;
}

function mapAttemptReasonCode(code: string, summary?: string): string {
    if (code === "ACCUSATION_PREREQS_MISSING") {
        return "you still need contradiction support before accusing";
    }
    if (code === "RECOVERY_PREREQS_MISSING") {
        return "you need one or two more corroborated clues first";
    }
    if (code === "RUNTIME_NOT_READY") return "connection not ready";
    if (code === "INVALID_COMMAND") return "that action was not valid in the current case state";
    if (summary && summary.trim().length > 0) return summary;
    return "blocked by current case rules";
}

function humanizeToken(value: string): string {
    const normalized = value
        .replace(/^[a-z]+:/, "")
        .replace(/_/g, " ")
        .trim();
    if (normalized.length === 0) return value;
    return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function renderSection(panel: HTMLElement, title: string, rows: string[]): void {
    if (rows.length === 0) return;
    renderSectionTitle(panel, title);
    const list = document.createElement("div");
    list.className = "resolution-list";
    for (const rowText of rows) {
        const row = document.createElement("div");
        row.className = "resolution-row";
        row.textContent = rowText;
        list.appendChild(row);
    }
    panel.appendChild(list);
}

function renderSectionTitle(panel: HTMLElement, label: string): void {
    const title = document.createElement("div");
    title.className = "resolution-section-title";
    title.textContent = label;
    panel.appendChild(title);
}

function renderLines(panel: HTMLElement, rows: Array<[string, string]>): void {
    for (const [labelText, valueText] of rows) {
        const row = document.createElement("div");
        row.className = "resolution-line";

        const label = document.createElement("span");
        label.className = "resolution-label";
        label.textContent = labelText;
        row.appendChild(label);

        const value = document.createElement("span");
        value.className = "resolution-value";
        value.textContent = valueText;
        row.appendChild(value);

        panel.appendChild(row);
    }
}

function renderInfo(panel: HTMLElement, text: string): void {
    const line = document.createElement("div");
    line.className = "resolution-info";
    line.textContent = text;
    panel.appendChild(line);
}
