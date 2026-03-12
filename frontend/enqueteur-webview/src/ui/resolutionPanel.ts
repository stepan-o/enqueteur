import type { WorldState, WorldStore } from "../state/worldStore";
import { createScopedTranslator, getSharedLocaleStore } from "../i18n";

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

const FACT_LABEL_KEYS: Record<string, string> = {
    N1: "resolution.fact.N1",
    N2: "resolution.fact.N2",
    N3: "resolution.fact.N3",
    N4: "resolution.fact.N4",
    N5: "resolution.fact.N5",
    N6: "resolution.fact.N6",
    N7: "resolution.fact.N7",
    N8: "resolution.fact.N8",
};

const EVIDENCE_LABEL_KEYS: Record<string, string> = {
    E1_TORN_NOTE: "resolution.evidence.E1_TORN_NOTE",
    E2_CAFE_RECEIPT: "resolution.evidence.E2_CAFE_RECEIPT",
    E3_METHOD_TRACE: "resolution.evidence.E3_METHOD_TRACE",
};

const SUSPECT_LABEL_KEYS: Record<string, string> = {
    laurent: "resolution.suspect.laurent",
    samira: "resolution.suspect.samira",
    outsider: "resolution.suspect.outsider",
};

const localeStore = getSharedLocaleStore();
const t = createScopedTranslator(() => localeStore.getLocale());

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

type DemoOutcomeView = {
    title: string;
    subtitle: string;
    tone: "good" | "mixed" | "incomplete";
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
        const isDemoProfile = presentationProfile === "demo";
        title.textContent = isDemoProfile ? t("resolution.title.case_outcome") : t("resolution.title.final_decision");
        panel.appendChild(title);

        const recap = lastState.caseRecap;
        const outcome = lastState.caseOutcome;
        const detailed = !isDemoProfile;
        const dispatchAllowed = canDispatch();
        const readiness = buildResolutionReadiness(lastState, recap, outcome, {
            canDispatch: dispatchAllowed,
            hasRecoveryDispatcher: Boolean(opts.dispatchAttemptRecovery),
            hasAccusationDispatcher: Boolean(opts.dispatchAttemptAccusation),
        });
        if (!recap && !outcome) {
            renderInfo(panel, t("resolution.info.outcome_unavailable"));
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
        const demoOutcome = buildDemoOutcomeView(finalOutcome, path, recap?.soft_fail.triggered ?? false, bestAwarded);

        if (isDemoProfile) {
            renderDemoOutcomeHero(panel, demoOutcome);
            renderInfo(panel, summarizeOutcome(finalOutcome, path, recap?.soft_fail.triggered ?? false, bestAwarded));
        } else {
            renderLines(panel, [
                [t("resolution.line.case_state"), `v${truthEpoch}`],
                [t("resolution.line.outcome"), `${demoOutcome.title} (${finalOutcome})`],
                [t("resolution.line.resolution_path"), `${humanizeToken(path)} (${path})`],
                [t("resolution.line.status"), available ? t("resolution.value.resolved") : t("resolution.value.in_progress")],
                [
                    t("resolution.line.contradiction"),
                    contradictionUsed
                        ? t("resolution.value.used")
                        : (contradictionSatisfied ? t("resolution.value.satisfied") : t("resolution.value.pending")),
                ],
                [t("resolution.line.best_outcome"), bestAwarded ? t("resolution.value.earned") : t("resolution.value.not_earned")],
            ]);
            renderInfo(panel, summarizeOutcome(finalOutcome, path, recap?.soft_fail.triggered ?? false, bestAwarded));
        }
        renderSectionTitle(panel, isDemoProfile ? t("resolution.section.final_call") : t("resolution.section.readiness"));
        renderLines(panel, isDemoProfile
            ? [
                [t("resolution.line.recovery"), formatAttemptReadiness(readiness.recovery)],
                [t("resolution.line.accusation"), formatAttemptReadiness(readiness.accusation)],
                [
                    t("resolution.line.support"),
                    t("resolution.support.counts", {
                        factCount: readiness.supportFactCount,
                        evidenceCount: readiness.supportEvidenceCount,
                    }),
                ],
                [
                    t("resolution.line.contradiction"),
                    readiness.contradictionRequired
                        ? (readiness.contradictionSatisfied ? t("resolution.value.ready") : t("resolution.value.still_needed"))
                        : t("resolution.value.not_required"),
                ],
            ]
            : [
                [t("resolution.line.recovery"), `${readiness.recovery.state} - ${readiness.recovery.reason}`],
                [t("resolution.line.accusation"), `${readiness.accusation.state} - ${readiness.accusation.reason}`],
                [t("resolution.line.support"), t("resolution.support.short", {
                    factCount: readiness.supportFactCount,
                    evidenceCount: readiness.supportEvidenceCount,
                })],
                [
                    t("resolution.line.contradiction"),
                    readiness.contradictionRequired
                        ? (readiness.contradictionSatisfied ? t("resolution.value.ready") : t("resolution.value.pending"))
                        : t("resolution.value.not_required"),
                ],
            ]);
        renderResolutionActions(panel, readiness, detailed);

        if (!recap) {
            return;
        }
        if (!recap.available) {
            renderInfo(panel, t("resolution.info.recap_pending"));
            return;
        }

        if (isDemoProfile) {
            renderSection(panel, t("resolution.section.what_happened"), buildOutcomeWhyRows(recap, outcome));
            renderSection(panel, t("resolution.section.what_you_proved"), [
                ...recap.key_fact_ids.map((factId) => formatFactLabel(factId, false)),
                ...recap.key_evidence_ids.map((evidenceId) => formatEvidenceLabel(evidenceId, false)),
            ]);
            renderSection(panel, t("resolution.section.what_mattered"), [
                ...recap.key_action_flags.map((flag) => formatActionFlag(flag, false)),
                ...recap.contradiction_action_flags.map((flag) => formatActionFlag(flag, false)),
                ...recap.relationship_result_flags.map((flag) => formatOutcomeFlag(flag, false)),
                ...recap.continuity_flags.map((flag) => formatOutcomeFlag(flag, false)),
            ]);
        } else {
            renderSection(panel, t("resolution.section.why_this_ending"), buildOutcomeWhyRows(recap, outcome));
            renderSection(panel, t("resolution.section.key_facts"), recap.key_fact_ids.map((factId) => formatFactLabel(factId, true)));
            renderSection(panel, t("resolution.section.key_evidence"), recap.key_evidence_ids.map((evidenceId) => formatEvidenceLabel(evidenceId, true)));
            renderSection(panel, t("resolution.section.path_highlights"), [
                ...recap.key_action_flags.map((flag) => formatActionFlag(flag, true)),
                ...recap.contradiction_action_flags.map((flag) => formatActionFlag(flag, true)),
            ]);
            renderSection(panel, t("resolution.section.aftermath"), [
                ...recap.relationship_result_flags.map((flag) => formatOutcomeFlag(flag, true)),
                ...recap.continuity_flags.map((flag) => formatOutcomeFlag(flag, true)),
            ]);
        }

        const markers: string[] = [];
        if (recap.best_outcome.awarded) markers.push("best_outcome_awarded");
        if (recap.best_outcome.quiet_recovery) markers.push("quiet_recovery");
        if (recap.best_outcome.no_public_escalation) markers.push("no_public_escalation");
        if (recap.best_outcome.strong_key_trust) markers.push("strong_key_trust");
        if (markers.length > 0) {
            renderSection(
                panel,
                isDemoProfile ? t("resolution.section.why_went_well") : t("resolution.section.best_markers"),
                markers.map((marker) => formatBestOutcomeMarker(marker, detailed))
            );
        }
        if (recap.soft_fail.triggered) {
            renderSection(
                panel,
                isDemoProfile ? t("resolution.section.what_went_wrong") : t("resolution.section.setback_triggers"),
                recap.soft_fail.trigger_conditions.map((trigger) => formatSoftFailTrigger(trigger, detailed))
            );
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
        renderSectionTitle(panelEl, t("resolution.section.final_actions"));

        const info = document.createElement("div");
        info.className = "resolution-info";
        info.textContent = readiness.terminal
            ? t("resolution.action.case_closed")
            : t("resolution.action.use_recovery_or_accusation");
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
        recoveryBtn.textContent = pendingAction ? t("resolution.action.sending") : t("resolution.action.attempt_recovery");
        recoveryBtn.disabled = pendingAction || readiness.recovery.state === "blocked";
        recoveryBtn.addEventListener("click", () => {
            if (!lastState || !opts.dispatchAttemptRecovery) return;
            pendingAction = true;
            lastActionMessage = t("resolution.action.sending_recovery");
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
                lastActionMessage = t("resolution.action.recovery_send_error", { message });
                render();
            });
        });
        row.appendChild(recoveryBtn);

        const suspect = document.createElement("select");
        suspect.className = "flow-action-btn";
        for (const suspectId of ["laurent", "samira", "outsider"]) {
            const option = document.createElement("option");
            option.value = suspectId;
            option.textContent = labelForSuspect(suspectId);
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
        accusationBtn.textContent = pendingAction ? t("resolution.action.sending") : t("resolution.action.attempt_accusation");
        accusationBtn.disabled = pendingAction || readiness.accusation.state === "blocked";
        accusationBtn.addEventListener("click", () => {
            if (!lastState || !opts.dispatchAttemptAccusation) return;
            pendingAction = true;
            lastActionMessage = t("resolution.action.sending_accusation");
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
                lastActionMessage = t("resolution.action.accusation_send_error", { message });
                render();
            });
        });
        row.appendChild(accusationBtn);

        panelEl.appendChild(row);
        renderInfo(panelEl, t("resolution.action.recovery_status", {
            status: formatAttemptReadiness(readiness.recovery),
        }));
        renderInfo(panelEl, t("resolution.action.accusation_status", {
            status: formatAttemptReadiness(readiness.accusation),
        }));
    };

    const unsub = store.subscribe((state) => {
        lastState = state;
        render();
    });
    let localeReady = false;
    const unsubLocale = localeStore.subscribe(() => {
        if (!localeReady) {
            localeReady = true;
            return;
        }
        render();
    });
    root.addEventListener("DOMNodeRemoved", () => {
        unsub();
        unsubLocale();
    }, { once: true });

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

function buildDemoOutcomeView(
    outcomeType: string,
    path: string,
    softFailTriggered: boolean,
    bestAwarded: boolean
): DemoOutcomeView {
    if (outcomeType === "best_outcome" || bestAwarded) {
        return {
            title: t("resolution.outcome.best.title"),
            subtitle: t("resolution.outcome.best.subtitle"),
            tone: "good",
        };
    }
    if (outcomeType === "recovery_success") {
        return {
            title: t("resolution.outcome.recovery.title"),
            subtitle: t("resolution.outcome.recovery.subtitle"),
            tone: "good",
        };
    }
    if (outcomeType === "accusation_success") {
        return {
            title: t("resolution.outcome.accusation.title"),
            subtitle: t("resolution.outcome.accusation.subtitle"),
            tone: "good",
        };
    }
    if (outcomeType === "soft_fail" || softFailTriggered) {
        return {
            title: t("resolution.outcome.soft_fail.title"),
            subtitle: t("resolution.outcome.soft_fail.subtitle"),
            tone: "mixed",
        };
    }
    if (path === "in_progress") {
        return {
            title: t("resolution.outcome.in_progress.title"),
            subtitle: t("resolution.outcome.in_progress.subtitle"),
            tone: "incomplete",
        };
    }
    return {
        title: t("resolution.outcome.updated.title"),
        subtitle: t("resolution.outcome.updated.subtitle"),
        tone: "incomplete",
    };
}

function renderDemoOutcomeHero(panel: HTMLElement, view: DemoOutcomeView): void {
    const card = document.createElement("div");
    card.className = "resolution-outcome-hero";
    card.dataset.tone = view.tone;

    const title = document.createElement("div");
    title.className = "resolution-outcome-title";
    title.textContent = view.title;

    const subtitle = document.createElement("div");
    subtitle.className = "resolution-outcome-subtitle";
    subtitle.textContent = view.subtitle;

    card.append(title, subtitle);
    panel.appendChild(card);
}

function formatAttemptReadiness(readiness: AttemptReadiness): string {
    if (readiness.state === "available") return t("resolution.readiness.available", { reason: readiness.reason });
    if (readiness.state === "risky") return t("resolution.readiness.risky", { reason: readiness.reason });
    return t("resolution.readiness.blocked", { reason: readiness.reason });
}

function formatFactLabel(factId: string, detailed: boolean): string {
    const label = FACT_LABEL_KEYS[factId] ? t(FACT_LABEL_KEYS[factId]) : humanizeToken(factId);
    return detailed ? `${label} (${factId})` : label;
}

function formatEvidenceLabel(evidenceId: string, detailed: boolean): string {
    const label = EVIDENCE_LABEL_KEYS[evidenceId] ? t(EVIDENCE_LABEL_KEYS[evidenceId]) : humanizeToken(evidenceId);
    return detailed ? `${label} (${evidenceId})` : label;
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
        ? t("resolution.reason.case_closed")
        : !opts.canDispatch
          ? t("resolution.reason.live_not_ready")
          : "";

    const recovery: AttemptReadiness = (() => {
        if (baseBlockedReason.length > 0) return { state: "blocked", reason: baseBlockedReason };
        if (!opts.hasRecoveryDispatcher) return { state: "blocked", reason: t("resolution.reason.recovery_unavailable") };
        if (knownFacts.length < 2 || knownEvidence.length < 1) {
            return { state: "risky", reason: t("resolution.reason.recovery_risky") };
        }
        return { state: "available", reason: t("resolution.reason.recovery_available") };
    })();

    const accusation: AttemptReadiness = (() => {
        if (baseBlockedReason.length > 0) return { state: "blocked", reason: baseBlockedReason };
        if (!opts.hasAccusationDispatcher) return { state: "blocked", reason: t("resolution.reason.accusation_unavailable") };
        if (contradictionRequired && !contradictionSatisfied) {
            return { state: "blocked", reason: t("resolution.reason.need_contradiction") };
        }
        if (knownFacts.length < 3 || knownEvidence.length < 1) {
            return { state: "risky", reason: t("resolution.reason.accusation_risky") };
        }
        return { state: "available", reason: t("resolution.reason.accusation_available") };
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
        return t("resolution.summary.best");
    }
    if (outcomeType === "recovery_success") {
        return t("resolution.summary.recovery");
    }
    if (outcomeType === "accusation_success") {
        return t("resolution.summary.accusation");
    }
    if (outcomeType === "soft_fail" || softFailTriggered) {
        return t("resolution.summary.soft_fail");
    }
    if (path === "in_progress") {
        return t("resolution.summary.in_progress");
    }
    return t("resolution.summary.updated");
}

function buildOutcomeWhyRows(
    recap: NonNullable<WorldState["caseRecap"]>,
    outcome: WorldState["caseOutcome"]
): string[] {
    const rows: string[] = [];
    rows.push(t("resolution.why.final_path", { path: humanizeToken(recap.resolution_path) }));
    rows.push(
        t("resolution.why.corroboration_used", {
            factCount: recap.key_fact_ids.length,
            evidenceCount: recap.key_evidence_ids.length,
        })
    );
    rows.push(
        recap.contradiction_requirement_satisfied
            ? t("resolution.why.contradiction_satisfied")
            : t("resolution.why.contradiction_incomplete")
    );
    if (recap.contradiction_used) {
        rows.push(t("resolution.why.contradiction_used"));
    }
    if (recap.soft_fail.triggered) {
        rows.push(t("resolution.why.setback_pressure"));
    }
    if (outcome?.public_escalation) {
        rows.push(t("resolution.why.public_escalation"));
    }
    return rows;
}

function formatActionFlag(flag: string, detailed: boolean): string {
    const known: Record<string, string> = {
        "action:recover_medallion": t("resolution.action_flag.recover_medallion"),
        "action:accuse_samira": t("resolution.action_flag.accuse_samira"),
        "action:state_contradiction_N3_N4": t("resolution.action_flag.contradiction_n3_n4"),
    };
    if (known[flag]) return detailed ? `${known[flag]} (${flag})` : known[flag];
    return detailed ? `${humanizeToken(flag)} (${flag})` : humanizeToken(flag);
}

function formatOutcomeFlag(flag: string, detailed: boolean): string {
    const known: Record<string, string> = {
        "continuity:quiet_recovery": t("resolution.outcome_flag.quiet_recovery"),
        "continuity:strong_key_trust": t("resolution.outcome_flag.strong_key_trust"),
        rel_elodie_positive: t("resolution.outcome_flag.rel_elodie_positive"),
        rel_marc_positive: t("resolution.outcome_flag.rel_marc_positive"),
    };
    if (known[flag]) return detailed ? `${known[flag]} (${flag})` : known[flag];
    return detailed ? `${humanizeToken(flag)} (${flag})` : humanizeToken(flag);
}

function formatSoftFailTrigger(trigger: string, detailed: boolean): string {
    const known: Record<string, string> = {
        item_left_building: t("resolution.soft_fail.item_left_building"),
        public_escalation: t("resolution.soft_fail.public_escalation"),
    };
    if (known[trigger]) return detailed ? `${known[trigger]} (${trigger})` : known[trigger];
    return detailed ? `${humanizeToken(trigger)} (${trigger})` : humanizeToken(trigger);
}

function formatBestOutcomeMarker(marker: string, detailed: boolean): string {
    const known: Record<string, string> = {
        best_outcome_awarded: t("resolution.best_marker.best_outcome_awarded"),
        quiet_recovery: t("resolution.best_marker.quiet_recovery"),
        no_public_escalation: t("resolution.best_marker.no_public_escalation"),
        strong_key_trust: t("resolution.best_marker.strong_key_trust"),
    };
    if (known[marker]) return detailed ? `${known[marker]} (${marker})` : known[marker];
    return detailed ? `${humanizeToken(marker)} (${marker})` : humanizeToken(marker);
}

function formatAttemptResult(
    kind: "recovery" | "accusation",
    result: ResolutionAttemptResult,
    detailed: boolean
): string {
    const title = kind === "recovery" ? t("resolution.line.recovery") : t("resolution.line.accusation");
    if (result.status === "accepted" || result.status === "submitted") {
        return detailed
            ? t("resolution.result.sent_detailed", { title, code: result.code })
            : t("resolution.result.sent", { title });
    }
    if (result.status === "blocked") {
        const reason = mapAttemptReasonCode(result.code, result.summary);
        return detailed
            ? t("resolution.result.blocked_detailed", { title, reason, code: result.code })
            : t("resolution.result.blocked", { title, reason });
    }
    if (result.status === "invalid") {
        return detailed
            ? t("resolution.result.invalid_detailed", { title, code: result.code })
            : t("resolution.result.invalid", { title });
    }
    if (result.status === "unavailable") {
        return detailed
            ? t("resolution.result.unavailable_detailed", { title, code: result.code })
            : t("resolution.result.unavailable", { title });
    }
    if (result.status === "error") {
        return detailed
            ? t("resolution.result.error_detailed", {
                title,
                summary: result.summary ?? t("resolution.result.unknown_error"),
                code: result.code,
            })
            : t("resolution.result.error", {
                title,
                summary: result.summary ?? t("resolution.result.unknown_error"),
            });
    }
    return detailed
        ? t("resolution.result.default_detailed", {
            title,
            summary: result.summary ?? t("resolution.result.command_processed"),
            code: result.code,
        })
        : t("resolution.result.default", {
            title,
            summary: result.summary ?? t("resolution.result.command_processed"),
        });
}

function mapAttemptReasonCode(code: string, summary?: string): string {
    if (code === "ACCUSATION_PREREQS_MISSING") {
        return t("resolution.reason.need_contradiction");
    }
    if (code === "RECOVERY_PREREQS_MISSING") {
        return t("resolution.reason.need_more_clues");
    }
    if (code === "RUNTIME_NOT_READY") return t("resolution.reason.connection_not_ready");
    if (code === "INVALID_COMMAND") return t("resolution.reason.invalid_command");
    if (summary && summary.trim().length > 0) return summary;
    return t("resolution.reason.blocked_by_rules");
}

function labelForSuspect(suspectId: string): string {
    const key = SUSPECT_LABEL_KEYS[suspectId];
    return key ? t(key) : suspectId;
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
