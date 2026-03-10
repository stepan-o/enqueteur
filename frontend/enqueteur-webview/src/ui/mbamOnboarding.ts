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

export type MbamObjectGuide = {
    object_id: string;
    label: string;
    location_hint: string;
    starter_priority: number;
    contradiction_relevant?: boolean;
};

const CASE_TITLE = "MBAM / Le Petit Vol du Musee";
const CASE_SUMMARY = "Recover the missing medallion by building a corroborated timeline.";
const MBAM_OBJECT_GUIDES: MbamObjectGuide[] = [
    {
        object_id: "O1_DISPLAY_CASE",
        label: "Display Case",
        location_hint: "Gallery floor",
        starter_priority: 1,
    },
    {
        object_id: "O3_WALL_LABEL",
        label: "Wall Label",
        location_hint: "Near the display case",
        starter_priority: 2,
    },
    {
        object_id: "O6_BADGE_TERMINAL",
        label: "Badge Terminal",
        location_hint: "Security office",
        starter_priority: 3,
        contradiction_relevant: true,
    },
    {
        object_id: "O9_RECEIPT_PRINTER",
        label: "Receipt Printer",
        location_hint: "Cafe counter",
        starter_priority: 4,
        contradiction_relevant: true,
    },
    {
        object_id: "O4_BENCH",
        label: "Bench",
        location_hint: "Public gallery seating",
        starter_priority: 5,
    },
    {
        object_id: "O10_BULLETIN_BOARD",
        label: "Bulletin Board",
        location_hint: "Public staff notice area",
        starter_priority: 6,
    },
];
const ACTION_LABELS: Record<string, string> = {
    inspect: "Inspect",
    check_lock: "Check lock",
    examine_surface: "Examine surface",
    read: "Read",
    request_access: "Request access",
    view_logs: "View logs",
    ask_for_receipt: "Ask for receipt",
    read_receipt: "Read receipt",
};
const ACTION_HINTS: Record<string, string> = {
    inspect: "Use this to gather baseline scene clues.",
    check_lock: "Useful for confirming tamper/timing details.",
    examine_surface: "Look for traces that support timeline reasoning.",
    read: "Extract concrete anchors (names, times, labels).",
    request_access: "Opens procedural paths when logs are gated.",
    view_logs: "Strong source for contradiction timeline checks.",
    ask_for_receipt: "Can surface corroborating purchase records.",
    read_receipt: "Use receipt time/item to support dialogue claims.",
};
const CONTRADICTION_EDGE_LABELS: Record<string, string> = {
    E3: "Potential timeline mismatch",
};

export function listMbamObjectGuides(): MbamObjectGuide[] {
    return [...MBAM_OBJECT_GUIDES];
}

export function getMbamObjectGuide(objectId: string): MbamObjectGuide | null {
    return MBAM_OBJECT_GUIDES.find((row) => row.object_id === objectId) ?? null;
}

export function labelMbamAction(actionId: string): string {
    return ACTION_LABELS[actionId] ?? actionId;
}

export function hintMbamAction(actionId: string): string {
    return ACTION_HINTS[actionId] ?? "Run this action to progress investigation context.";
}

export function labelMbamContradictionEdge(edgeId: string): string {
    return CONTRADICTION_EDGE_LABELS[edgeId] ?? edgeId;
}

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
