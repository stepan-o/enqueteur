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

export type MbamCaseSetupGuide = {
    incident: string;
    firstInspect: string;
    firstTalkTo: string;
    progressionPath: string[];
};

export type MbamPlaytestPathStep = {
    id:
        | "starter_investigation"
        | "first_dialogue"
        | "first_minigame"
        | "contradiction_ready"
        | "resolution_attempted"
        | "recap_available";
    label: string;
    done: boolean;
};

export type MbamPlaytestPathView = {
    title: string;
    currentMilestone: string;
    steps: MbamPlaytestPathStep[];
};

export type MbamObjectGuide = {
    object_id: string;
    label: string;
    location_hint: string;
    starter_priority: number;
    contradiction_relevant?: boolean;
};

const CASE_TITLE = "MBAM / Le Petit Vol du Musee";
const CASE_SUMMARY = "Recover the missing medallion by piecing together a reliable timeline.";
const CASE_INCIDENT = "A gallery medallion is missing shortly before closing.";
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
    inspect: "Start here to spot what changed at the scene.",
    check_lock: "Confirm whether the case was tampered with.",
    examine_surface: "Look for traces that clarify who handled the object.",
    read: "Capture concrete anchors like names, dates, and labels.",
    request_access: "Ask politely to unlock restricted records.",
    view_logs: "Use this to anchor movement times.",
    ask_for_receipt: "Can reveal a supporting timeline clue.",
    read_receipt: "Use receipt time/item to support your questioning.",
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
    return ACTION_HINTS[actionId] ?? "Try this action to move the investigation forward.";
}

export function labelMbamContradictionEdge(edgeId: string): string {
    return CONTRADICTION_EDGE_LABELS[edgeId] ?? edgeId;
}

export function buildMbamCaseSetupGuide(state: WorldState): MbamCaseSetupGuide {
    const investigation = state.investigation;
    const dialogue = state.dialogue;

    const displayCaseObserved = isAffordanceObserved(state, "O1_DISPLAY_CASE");
    const wallLabelObserved = isAffordanceObserved(state, "O3_WALL_LABEL");
    const badgeObserved = isAffordanceObserved(state, "O6_BADGE_TERMINAL");
    const receiptObserved = isAffordanceObserved(state, "O9_RECEIPT_PRINTER");
    const hasDialogueTurn = (dialogue?.recent_turns.length ?? 0) > 0;
    const contradictionRequired = investigation?.contradictions.required_for_accusation ?? false;
    const contradictionSatisfied = investigation?.contradictions.requirement_satisfied ?? false;

    const firstInspect = (() => {
        if (!displayCaseObserved && !wallLabelObserved) {
            return "Inspect the Display Case, then read the Wall Label in the gallery.";
        }
        if (!displayCaseObserved) {
            return "Inspect the Display Case in the gallery.";
        }
        if (!wallLabelObserved) {
            return "Read the Wall Label near the display case.";
        }
        if (!badgeObserved) {
            return "Check the Badge Terminal in the security office.";
        }
        if (!receiptObserved) {
            return "Check the Receipt Printer at the cafe counter.";
        }
        return "Continue with remaining object leads in Case Notes.";
    })();

    const firstTalkTo = (() => {
        if (!hasDialogueTurn) return "Talk to Elodie first to anchor what happened and when.";
        if (!badgeObserved) return "Talk to Marc if you need access to security logs.";
        if (contradictionRequired && !contradictionSatisfied) {
            return "Question timeline details, then challenge contradictions in surfaced scenes.";
        }
        return "Keep questioning witnesses to corroborate your timeline.";
    })();

    const progressionPath = [
        "Inspect scene objects to collect concrete clues.",
        "Use Conversations (in French) to test and confirm those clues.",
        "Cross-check timeline clues before final recovery or accusation attempts.",
    ];

    return {
        incident: CASE_INCIDENT,
        firstInspect,
        firstTalkTo,
        progressionPath,
    };
}

export function buildMbamPlaytestPathView(state: WorldState): MbamPlaytestPathView {
    const investigation = state.investigation;
    const dialogue = state.dialogue;
    const caseOutcome = state.caseOutcome;
    const caseRecap = state.caseRecap;

    const starterInvestigation =
        isAffordanceObserved(state, "O1_DISPLAY_CASE")
        && isAffordanceObserved(state, "O3_WALL_LABEL");
    const firstDialogue = (dialogue?.recent_turns.length ?? 0) > 0;
    const firstMinigame = Boolean(dialogue?.learning?.minigames.some((row) => row.completed));
    const contradictionReady = investigation?.contradictions.requirement_satisfied ?? false;
    const resolutionAttempted =
        (caseOutcome?.primary_outcome ?? "in_progress") !== "in_progress"
        || (caseRecap?.resolution_path ?? "in_progress") !== "in_progress";
    const recapAvailable = caseRecap?.available ?? Boolean(caseOutcome?.terminal);

    const steps: MbamPlaytestPathStep[] = [
        {
            id: "starter_investigation",
            label: "Inspect starter objects (Display Case + Wall Label).",
            done: starterInvestigation,
        },
        {
            id: "first_dialogue",
            label: "Talk to Elodie and submit your first dialogue turn.",
            done: firstDialogue,
        },
        {
            id: "first_minigame",
            label: "Complete at least one minigame from Case Notes.",
            done: firstMinigame,
        },
        {
            id: "contradiction_ready",
            label: "Reach contradiction-ready state for accusation path.",
            done: contradictionReady,
        },
        {
            id: "resolution_attempted",
            label: "Attempt Recovery or Attempt Accusation.",
            done: resolutionAttempted,
        },
        {
            id: "recap_available",
            label: "Review final recap and outcome rationale.",
            done: recapAvailable,
        },
    ];

    const nextStep = steps.find((row) => !row.done);
    const currentMilestone = nextStep
        ? `Next: ${nextStep.label}`
        : "Path complete: recap reviewed and ready for next internal run.";

    return {
        title: "Internal Playtest Path",
        currentMilestone,
        steps,
    };
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
            label: "Record your first clues in Case Notes.",
            done: clueProgress,
        },
        {
            id: "dialogue_turn",
            label: "Talk to Elodie first in Conversations (in French).",
            done: hasDialogueTurn,
        },
        {
            id: "contradiction_readiness",
            label: "Cross-check timeline clues and prepare a contradiction.",
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
    if (!ctx.hasBaseline) return "Setting the scene...";
    if (ctx.isTerminal) return "Case closed. Review the final decision recap.";
    if (!ctx.displayCaseObserved) return "Begin in the gallery: inspect the Display Case.";
    if (!ctx.wallLabelObserved) return "Read the Wall Label and note title/date anchors.";
    if (!ctx.clueProgress) return "Follow object leads to uncover your first clues.";
    if (!ctx.hasDialogueTurn) return "Open Conversations and talk to Elodie first in French.";
    if (ctx.contradictionRequired && !ctx.contradictionSatisfied) {
        if (ctx.contradictionUnlockable) return "You have a contradiction lead. Tighten your timeline next.";
        return "Build a stronger contradiction before making an accusation.";
    }
    return "Keep corroborating clues before making your final decision.";
}

function isAffordanceObserved(state: WorldState, objectId: string): boolean {
    const row = state.investigation?.objects.find((objectState) => objectState.object_id === objectId);
    if (!row) return false;
    return row.observed_affordances.length > 0;
}
