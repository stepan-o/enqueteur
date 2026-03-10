import type { WorldState } from "../state/worldStore";

export type MbamOnboardingStep = {
    id: "inspect_starters" | "log_clues" | "dialogue_turn" | "contradiction_readiness";
    label: string;
    done: boolean;
};

export type MbamOnboardingView = {
    caseTitle: string;
    caseSummary: string;
    currentLead: string;
    steps: MbamOnboardingStep[];
};

const CASE_TITLE = "MBAM / Le Petit Vol du Musee";
const CASE_SUMMARY = "Recover the missing medallion by building a corroborated timeline.";

export function buildMbamOnboardingView(state: WorldState): MbamOnboardingView {
    const investigation = state.investigation;
    const dialogue = state.dialogue;
    const caseOutcome = state.caseOutcome;

    const displayCaseObserved = isAffordanceObserved(state, "O1_DISPLAY_CASE");
    const wallLabelObserved = isAffordanceObserved(state, "O3_WALL_LABEL");

    const knownFacts = investigation?.facts.known_fact_ids ?? [];
    const startingFacts = new Set(state.caseState?.visible_case_slice.starting_known_fact_ids ?? []);
    const newlyLearnedFactCount = knownFacts.filter((factId) => !startingFacts.has(factId)).length;

    const discoveredEvidence = investigation?.evidence.discovered_ids.length ?? 0;
    const collectedEvidence = investigation?.evidence.collected_ids.length ?? 0;
    const clueProgress = newlyLearnedFactCount > 0 || discoveredEvidence > 0 || collectedEvidence > 0;

    const hasDialogueTurn = (dialogue?.recent_turns.length ?? 0) > 0;

    const contradictionKnown = (investigation?.contradictions.known_edge_ids.length ?? 0) > 0;
    const contradictionUnlockable = (investigation?.contradictions.unlockable_edge_ids.length ?? 0) > 0;
    const contradictionSatisfied = investigation?.contradictions.requirement_satisfied ?? false;
    const contradictionProgress = contradictionKnown || contradictionUnlockable || contradictionSatisfied;

    const steps: MbamOnboardingStep[] = [
        {
            id: "inspect_starters",
            label: "Inspect the Display Case and Wall Label in the gallery.",
            done: displayCaseObserved && wallLabelObserved,
        },
        {
            id: "log_clues",
            label: "Collect your first clues in Case Notes (facts/evidence).",
            done: clueProgress,
        },
        {
            id: "dialogue_turn",
            label: "Use Conversations to submit a structured French turn.",
            done: hasDialogueTurn,
        },
        {
            id: "contradiction_readiness",
            label: "Cross-check timeline clues and contradiction readiness.",
            done: contradictionProgress,
        },
    ];

    return {
        caseTitle: CASE_TITLE,
        caseSummary: CASE_SUMMARY,
        currentLead: resolveCurrentLead({
            hasBaseline: Boolean(investigation && dialogue),
            isTerminal: Boolean(caseOutcome?.terminal),
            displayCaseObserved,
            wallLabelObserved,
            clueProgress,
            hasDialogueTurn,
            contradictionRequired: investigation?.contradictions.required_for_accusation ?? false,
            contradictionSatisfied,
            contradictionUnlockable,
        }),
        steps,
    };
}

function resolveCurrentLead(ctx: {
    hasBaseline: boolean;
    isTerminal: boolean;
    displayCaseObserved: boolean;
    wallLabelObserved: boolean;
    clueProgress: boolean;
    hasDialogueTurn: boolean;
    contradictionRequired: boolean;
    contradictionSatisfied: boolean;
    contradictionUnlockable: boolean;
}): string {
    if (!ctx.hasBaseline) return "Waiting for case baseline...";
    if (ctx.isTerminal) return "Case resolved. Review the Decision Board recap.";
    if (!ctx.displayCaseObserved) return "Begin in the gallery: inspect the Display Case.";
    if (!ctx.wallLabelObserved) return "Read the Wall Label and note title/date anchors.";
    if (!ctx.clueProgress) return "Follow object actions to surface your first clues.";
    if (!ctx.hasDialogueTurn) return "Open Conversations and submit one French turn.";
    if (ctx.contradictionRequired && !ctx.contradictionSatisfied) {
        if (ctx.contradictionUnlockable) return "Timeline clues can unlock contradictions. Press that path next.";
        return "Build contradiction readiness before attempting accusation.";
    }
    return "Keep corroborating facts before a final resolution attempt.";
}

function isAffordanceObserved(state: WorldState, objectId: string): boolean {
    const row = state.investigation?.objects.find((objectState) => objectState.object_id === objectId);
    if (!row) return false;
    return row.observed_affordances.length > 0;
}
