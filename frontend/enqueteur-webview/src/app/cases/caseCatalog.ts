import type { EnqueteurCaseId } from "../appState";

export type PreGameCaseEntry = {
    caseId: EnqueteurCaseId;
    code: string;
    label: string;
    subtitle: string;
};

export const PRE_GAME_CASES: readonly PreGameCaseEntry[] = [
    {
        caseId: "MBAM_01",
        code: "MBAM",
        label: "Le Petit Vol du Musée",
        subtitle: "Musée des Beaux-Arts de Montréal",
    },
];
