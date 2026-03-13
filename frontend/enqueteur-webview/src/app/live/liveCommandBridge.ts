import type { InputCommandPayload } from "./enqueteurLiveClient";

export type LiveCommandSubmission = {
    accepted: boolean;
    clientCmdId: string;
    reasonCode?: string;
    message?: string;
    messageKey?: string;
    messageParams?: Record<string, unknown>;
};

export type LiveCommandBridge = {
    canSendInputCommand: () => boolean;
    sendInputCommand: (
        cmd: InputCommandPayload["cmd"],
        opts?: { tickTarget?: number }
    ) => Promise<LiveCommandSubmission>;
};
