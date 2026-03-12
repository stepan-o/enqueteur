import type { WorldState } from "../state/worldStore";
import { t } from "../i18n";

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

type ObjectGuideMeta = {
    object_id: string;
    label_key: string;
    location_hint_key: string;
    starter_priority: number;
    contradiction_relevant?: boolean;
};

const MBAM_OBJECT_GUIDE_META: ObjectGuideMeta[] = [
    {
        object_id: "O1_DISPLAY_CASE",
        label_key: "mbam.object.O1_DISPLAY_CASE.label",
        location_hint_key: "mbam.object.O1_DISPLAY_CASE.location",
        starter_priority: 1,
    },
    {
        object_id: "O3_WALL_LABEL",
        label_key: "mbam.object.O3_WALL_LABEL.label",
        location_hint_key: "mbam.object.O3_WALL_LABEL.location",
        starter_priority: 2,
    },
    {
        object_id: "O6_BADGE_TERMINAL",
        label_key: "mbam.object.O6_BADGE_TERMINAL.label",
        location_hint_key: "mbam.object.O6_BADGE_TERMINAL.location",
        starter_priority: 3,
        contradiction_relevant: true,
    },
    {
        object_id: "O9_RECEIPT_PRINTER",
        label_key: "mbam.object.O9_RECEIPT_PRINTER.label",
        location_hint_key: "mbam.object.O9_RECEIPT_PRINTER.location",
        starter_priority: 4,
        contradiction_relevant: true,
    },
    {
        object_id: "O4_BENCH",
        label_key: "mbam.object.O4_BENCH.label",
        location_hint_key: "mbam.object.O4_BENCH.location",
        starter_priority: 5,
    },
    {
        object_id: "O10_BULLETIN_BOARD",
        label_key: "mbam.object.O10_BULLETIN_BOARD.label",
        location_hint_key: "mbam.object.O10_BULLETIN_BOARD.location",
        starter_priority: 6,
    },
];

const ACTION_LABEL_KEYS: Record<string, string> = {
    inspect: "mbam.action.inspect.label",
    check_lock: "mbam.action.check_lock.label",
    examine_surface: "mbam.action.examine_surface.label",
    read: "mbam.action.read.label",
    request_access: "mbam.action.request_access.label",
    view_logs: "mbam.action.view_logs.label",
    ask_for_receipt: "mbam.action.ask_for_receipt.label",
    read_receipt: "mbam.action.read_receipt.label",
};

const ACTION_HINT_KEYS: Record<string, string> = {
    inspect: "mbam.action.inspect.hint",
    check_lock: "mbam.action.check_lock.hint",
    examine_surface: "mbam.action.examine_surface.hint",
    read: "mbam.action.read.hint",
    request_access: "mbam.action.request_access.hint",
    view_logs: "mbam.action.view_logs.hint",
    ask_for_receipt: "mbam.action.ask_for_receipt.hint",
    read_receipt: "mbam.action.read_receipt.hint",
};

const CONTRADICTION_EDGE_LABEL_KEYS: Record<string, string> = {
    E3: "mbam.contradiction.E3.label",
};

export function listMbamObjectGuides(): MbamObjectGuide[] {
    return MBAM_OBJECT_GUIDE_META.map(buildObjectGuide);
}

export function getMbamObjectGuide(objectId: string): MbamObjectGuide | null {
    const meta = MBAM_OBJECT_GUIDE_META.find((row) => row.object_id === objectId);
    return meta ? buildObjectGuide(meta) : null;
}

export function labelMbamAction(actionId: string): string {
    const key = ACTION_LABEL_KEYS[actionId];
    return key ? t(key) : actionId;
}

export function hintMbamAction(actionId: string): string {
    const key = ACTION_HINT_KEYS[actionId];
    if (!key) return t("mbam.action.default_hint");
    return t(key);
}

export function labelMbamContradictionEdge(edgeId: string): string {
    const key = CONTRADICTION_EDGE_LABEL_KEYS[edgeId];
    return key ? t(key) : edgeId;
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
            return t("mbam.setup.firstInspect.inspect_then_label");
        }
        if (!displayCaseObserved) {
            return t("mbam.setup.firstInspect.inspect_case");
        }
        if (!wallLabelObserved) {
            return t("mbam.setup.firstInspect.read_label");
        }
        if (!badgeObserved) {
            return t("mbam.setup.firstInspect.check_badge_terminal");
        }
        if (!receiptObserved) {
            return t("mbam.setup.firstInspect.check_receipt_printer");
        }
        return t("mbam.setup.firstInspect.continue_leads");
    })();

    const firstTalkTo = (() => {
        if (!hasDialogueTurn) return t("mbam.setup.firstTalkTo.elodie_first");
        if (!badgeObserved) return t("mbam.setup.firstTalkTo.marc_if_needed");
        if (contradictionRequired && !contradictionSatisfied) {
            return t("mbam.setup.firstTalkTo.challenge_contradictions");
        }
        return t("mbam.setup.firstTalkTo.keep_questioning");
    })();

    const progressionPath = [
        t("mbam.setup.progression.1"),
        t("mbam.setup.progression.2"),
        t("mbam.setup.progression.3"),
        t("mbam.setup.progression.4"),
        t("mbam.setup.progression.5"),
    ];

    return {
        incident: t("mbam.case.incident"),
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
            label: t("mbam.playtest.step.starter_investigation"),
            done: starterInvestigation,
        },
        {
            id: "first_dialogue",
            label: t("mbam.playtest.step.first_dialogue"),
            done: firstDialogue,
        },
        {
            id: "first_minigame",
            label: t("mbam.playtest.step.first_minigame"),
            done: firstMinigame,
        },
        {
            id: "contradiction_ready",
            label: t("mbam.playtest.step.contradiction_ready"),
            done: contradictionReady,
        },
        {
            id: "resolution_attempted",
            label: t("mbam.playtest.step.resolution_attempted"),
            done: resolutionAttempted,
        },
        {
            id: "recap_available",
            label: t("mbam.playtest.step.recap_available"),
            done: recapAvailable,
        },
    ];

    const nextStep = steps.find((row) => !row.done);
    const currentMilestone = nextStep
        ? t("mbam.playtest.current.next", { label: nextStep.label })
        : t("mbam.playtest.current.complete");

    return {
        title: t("mbam.playtest.title"),
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
            label: t("mbam.onboarding.step.inspect_starters"),
            done: displayCaseObserved && wallLabelObserved,
        },
        {
            id: "log_clues",
            label: t("mbam.onboarding.step.log_clues"),
            done: clueProgress,
        },
        {
            id: "dialogue_turn",
            label: t("mbam.onboarding.step.dialogue_turn"),
            done: hasDialogueTurn,
        },
        {
            id: "contradiction_readiness",
            label: t("mbam.onboarding.step.contradiction_readiness"),
            done: contradictionProgress,
        },
    ];

    return {
        caseTitle: t("mbam.case.title"),
        caseSummary: t("mbam.case.summary"),
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
    if (!ctx.hasBaseline) return t("mbam.currentLead.setting_scene");
    if (ctx.isTerminal) return t("mbam.currentLead.case_closed");
    if (!ctx.displayCaseObserved) return t("mbam.currentLead.inspect_display_case");
    if (!ctx.wallLabelObserved) return t("mbam.currentLead.read_wall_label");
    if (!ctx.clueProgress) return t("mbam.currentLead.follow_object_leads");
    if (!ctx.hasDialogueTurn) return t("mbam.currentLead.talk_elodie");
    if (ctx.contradictionRequired && !ctx.contradictionSatisfied) {
        if (ctx.contradictionUnlockable) return t("mbam.currentLead.contradiction_lead");
        return t("mbam.currentLead.build_contradiction");
    }
    return t("mbam.currentLead.keep_corroborating");
}

function buildObjectGuide(meta: ObjectGuideMeta): MbamObjectGuide {
    return {
        object_id: meta.object_id,
        label: t(meta.label_key),
        location_hint: t(meta.location_hint_key),
        starter_priority: meta.starter_priority,
        contradiction_relevant: meta.contradiction_relevant,
    };
}

function isAffordanceObserved(state: WorldState, objectId: string): boolean {
    const row = state.investigation?.objects.find((objectState) => objectState.object_id === objectId);
    if (!row) return false;
    return row.observed_affordances.length > 0;
}
