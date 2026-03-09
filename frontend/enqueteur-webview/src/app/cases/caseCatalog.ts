import type { EnqueteurCaseId } from "../appState";
import type { CaseLaunchDifficultyProfile, CaseLaunchMode } from "../api/caseLaunchClient";

export type CaseLaunchPreset = {
    seed: string | number;
    difficultyProfile: CaseLaunchDifficultyProfile;
    mode: CaseLaunchMode;
};

export type PreGameCaseEntry = {
    caseId: EnqueteurCaseId;
    code: string;
    label: string;
    subtitle: string;
    launchPreset: CaseLaunchPreset;
};

export const PRE_GAME_CASES: readonly PreGameCaseEntry[] = [
    {
        caseId: "MBAM_01",
        code: "MBAM",
        label: "Le Petit Vol du Musée",
        subtitle: "Musée des Beaux-Arts de Montréal",
        launchPreset: {
            seed: "A",
            difficultyProfile: "D0",
            mode: "playtest",
        },
    },
];

export function getPreGameCaseEntry(caseId: EnqueteurCaseId): PreGameCaseEntry | undefined {
    return PRE_GAME_CASES.find((entry) => entry.caseId === caseId);
}
