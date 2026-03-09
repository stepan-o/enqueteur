import { describe, expect, it, vi } from "vitest";

import {
    EnqueteurLiveClient,
    type EnqueteurInboundEnvelopeByType,
    type EnqueteurLiveClientWebSocket,
    KVP_VERSION,
} from "../app/live/enqueteurLiveClient";

class FakeWebSocket implements EnqueteurLiveClientWebSocket {
    static readonly CONNECTING = 0;
    static readonly OPEN = 1;
    static readonly CLOSING = 2;
    static readonly CLOSED = 3;

    readonly url: string;
    readyState = FakeWebSocket.CONNECTING;
    onopen: ((event: Event) => void) | null = null;
    onclose: ((event: CloseEvent) => void) | null = null;
    onerror: ((event: Event) => void) | null = null;
    onmessage: ((event: MessageEvent<unknown>) => void) | null = null;
    readonly sentFrames: string[] = [];

    constructor(url: string) {
        this.url = url;
    }

    send(data: string): void {
        this.sentFrames.push(data);
    }

    close(): void {
        this.readyState = FakeWebSocket.CLOSED;
        this.onclose?.({ code: 1000, reason: "closed" } as CloseEvent);
    }

    triggerOpen(): void {
        this.readyState = FakeWebSocket.OPEN;
        this.onopen?.(new Event("open"));
    }

    triggerMessage(data: unknown): void {
        this.onmessage?.({ data } as MessageEvent<unknown>);
    }
}

function makeEnvelope<T extends keyof EnqueteurInboundEnvelopeByType>(
    msgType: T,
    payload: EnqueteurInboundEnvelopeByType[T]["payload"]
): string {
    return JSON.stringify({
        kvp_version: KVP_VERSION,
        msg_type: msgType,
        msg_id: "msg-123",
        sent_at_ms: 123,
        payload,
    });
}

describe("Phase F1 Enqueteur live client", () => {
    it("connects and emits VIEWER_HELLO on socket open", () => {
        const ws = new FakeWebSocket("ws://localhost/live?run_id=run-123");
        const wsFactory = vi.fn(() => ws);
        const client = new EnqueteurLiveClient({
            url: "ws://localhost/live?run_id=run-123",
            websocketFactory: wsFactory,
        });

        client.connect();
        ws.triggerOpen();

        expect(wsFactory).toHaveBeenCalledWith("ws://localhost/live?run_id=run-123");
        expect(ws.sentFrames).toHaveLength(1);
        const sent = JSON.parse(ws.sentFrames[0]) as {
            kvp_version: string;
            msg_type: string;
            payload: { supported_schema_versions: string[] };
        };
        expect(sent.kvp_version).toBe("0.1");
        expect(sent.msg_type).toBe("VIEWER_HELLO");
        expect(sent.payload.supported_schema_versions).toEqual(["enqueteur_mbam_1"]);
    });

    it("dispatches inbound messages by msg_type", () => {
        const ws = new FakeWebSocket("ws://localhost/live?run_id=run-123");
        const client = new EnqueteurLiveClient({
            url: "ws://localhost/live?run_id=run-123",
            websocketFactory: () => ws,
        });
        const kernelHelloSpy = vi.fn();

        client.onMessage("KERNEL_HELLO", kernelHelloSpy);
        client.connect();
        ws.triggerOpen();
        ws.triggerMessage(
            makeEnvelope("KERNEL_HELLO", {
                engine_name: "enqueteur",
                engine_version: "0.1.0",
                schema_version: "enqueteur_mbam_1",
                world_id: "world-123",
                run_id: "run-123",
                seed: "A",
                tick_rate_hz: 30,
                time_origin_ms: 0,
                render_spec: {},
            })
        );

        expect(kernelHelloSpy).toHaveBeenCalledTimes(1);
        expect(kernelHelloSpy).toHaveBeenCalledWith(
            expect.objectContaining({
                msg_type: "KERNEL_HELLO",
                payload: expect.objectContaining({
                    engine_name: "enqueteur",
                    schema_version: "enqueteur_mbam_1",
                    run_id: "run-123",
                }),
            })
        );
    });

    it("rejects non-text, invalid JSON, and unknown message types deterministically", () => {
        const ws = new FakeWebSocket("ws://localhost/live?run_id=run-123");
        const client = new EnqueteurLiveClient({
            url: "ws://localhost/live?run_id=run-123",
            websocketFactory: () => ws,
            disconnectOnProtocolError: false,
        });
        const protocolErrors: string[] = [];
        client.onProtocolError((error) => {
            protocolErrors.push(error.code);
        });

        client.connect();
        ws.triggerOpen();
        ws.triggerMessage(new ArrayBuffer(8));
        ws.triggerMessage("{invalid-json}");
        ws.triggerMessage(
            JSON.stringify({
                kvp_version: "0.1",
                msg_type: "TOTALLY_UNKNOWN",
                msg_id: "msg-123",
                sent_at_ms: 123,
                payload: {},
            })
        );

        expect(protocolErrors).toEqual([
            "NON_TEXT_FRAME",
            "INVALID_JSON",
            "UNKNOWN_MSG_TYPE",
        ]);
    });
});
