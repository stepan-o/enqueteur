import type { EnqueteurCaseId } from "../appState";
import type { CaseLaunchDifficultyProfile, CaseLaunchMode } from "../api/caseLaunchClient";
import type { TranslationLookupKey } from "../../i18n";

export type CaseLaunchPreset = {
    seed: string | number;
    difficultyProfile: CaseLaunchDifficultyProfile;
    mode: CaseLaunchMode;
};

export type ExternalDemoPath = {
    id: string;
    seed: string | number;
    titleKey: TranslationLookupKey;
    summaryKey: TranslationLookupKey;
    beats: readonly string[];
    blockedStateHintKey: TranslationLookupKey;
};

export type PreGameCaseEntry = {
    caseId: EnqueteurCaseId;
    code: string;
    labelKey: TranslationLookupKey;
    subtitleKey: TranslationLookupKey;
    launchPreset: CaseLaunchPreset;
    defaultDemoPath: ExternalDemoPath;
};

export const MBAM_DEFAULT_EXTERNAL_DEMO_PATH: ExternalDemoPath = {
    id: "MBAM_DEMO_PATH_A",
    seed: "A",
    titleKey: "flow.demoPath.MBAM_DEMO_PATH_A.title",
    summaryKey: "flow.demoPath.MBAM_DEMO_PATH_A.summary",
    beats: [
        "Inspect Display Case and Wall Label.",
        "Talk to Elodie first in Conversations.",
        "Complete the Wall Label minigame in Case Notes.",
        "Use badge + receipt clues to unlock contradiction progress.",
        "Attempt Recovery or Accusation, then review recap.",
    ],
    blockedStateHintKey: "flow.demoPath.MBAM_DEMO_PATH_A.blockedHint",
};

export const PRE_GAME_CASES: readonly PreGameCaseEntry[] = [
    {
        caseId: "MBAM_01",
        code: "MBAM",
        labelKey: "flow.case.MBAM_01.label",
        subtitleKey: "flow.case.MBAM_01.subtitle",
        launchPreset: {
            seed: MBAM_DEFAULT_EXTERNAL_DEMO_PATH.seed,
            difficultyProfile: "D0",
            mode: "playtest",
        },
        defaultDemoPath: MBAM_DEFAULT_EXTERNAL_DEMO_PATH,
    },
];

export function getPreGameCaseEntry(caseId: EnqueteurCaseId): PreGameCaseEntry | undefined {
    return PRE_GAME_CASES.find((entry) => entry.caseId === caseId);
}
