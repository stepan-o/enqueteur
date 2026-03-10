import type { EnqueteurCaseId } from "../appState";
import type { CaseLaunchDifficultyProfile, CaseLaunchMode } from "../api/caseLaunchClient";

export type CaseLaunchPreset = {
    seed: string | number;
    difficultyProfile: CaseLaunchDifficultyProfile;
    mode: CaseLaunchMode;
};

export type ExternalDemoPath = {
    id: string;
    seed: string | number;
    title: string;
    summary: string;
    beats: readonly string[];
    blockedStateHint: string;
};

export type PreGameCaseEntry = {
    caseId: EnqueteurCaseId;
    code: string;
    label: string;
    subtitle: string;
    launchPreset: CaseLaunchPreset;
    defaultDemoPath: ExternalDemoPath;
};

export const MBAM_DEFAULT_EXTERNAL_DEMO_PATH: ExternalDemoPath = {
    id: "MBAM_DEMO_PATH_A",
    seed: "A",
    title: "Seed A / Gallery timeline route",
    summary: "Most readable external demo flow from first clue through final recap.",
    beats: [
        "Inspect Display Case and Wall Label.",
        "Talk to Elodie first in Conversations.",
        "Complete the Wall Label minigame in Case Notes.",
        "Use badge + receipt clues to unlock contradiction progress.",
        "Attempt Recovery or Accusation, then review recap.",
    ],
    blockedStateHint: "If blocked, follow the next lead shown in Case Notes and continue gathering corroboration.",
};

export const PRE_GAME_CASES: readonly PreGameCaseEntry[] = [
    {
        caseId: "MBAM_01",
        code: "MBAM",
        label: "Le Petit Vol du Musée",
        subtitle: "Musée des Beaux-Arts de Montréal",
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
