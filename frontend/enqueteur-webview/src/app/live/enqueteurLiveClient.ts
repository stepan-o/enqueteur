import {
    ENQUETEUR_ENGINE_NAME,
    ENQUETEUR_SCHEMA_VERSION,
} from "../api/caseLaunchClient";

export const KVP_VERSION = "0.1";

export type KvpVersion = typeof KVP_VERSION;

export type EnqueteurChannel =
    | "WORLD"
    | "NPCS"
    | "INVESTIGATION"
    | "DIALOGUE"
    | "LEARNING"
    | "EVENTS"
    | "DEBUG";

export type EnqueteurDiffPolicy =
    | "DIFF_ONLY"
    | "PERIODIC_SNAPSHOT"
    | "SNAPSHOT_ON_DESYNC";

export type EnqueteurSnapshotPolicy = "ON_JOIN" | "NEVER";
export type EnqueteurCompressionPolicy = "NONE";

export type ViewerHelloPayload = {
    viewer_name: string;
    viewer_version: string;
    supported_schema_versions: string[];
    supports: {
        diff_stream: boolean;
        full_snapshot: boolean;
        replay_seek: boolean;
    };
};

export type SubscribePayload = {
    stream: "LIVE";
    channels: EnqueteurChannel[];
    diff_policy: EnqueteurDiffPolicy;
    snapshot_policy: EnqueteurSnapshotPolicy;
    compression: EnqueteurCompressionPolicy;
};

export type InputCommandType =
    | "INVESTIGATE_OBJECT"
    | "DIALOGUE_TURN"
    | "MINIGAME_SUBMIT"
    | "ATTEMPT_RECOVERY"
    | "ATTEMPT_ACCUSATION";

export type InputCommandPayload = {
    client_cmd_id: string;
    tick_target: number;
    cmd: {
        type: InputCommandType;
        payload: Record<string, unknown>;
    };
};

export type KernelHelloPayload = {
    engine_name: string;
    engine_version: string;
    schema_version: string;
    world_id: string;
    run_id: string;
    seed: string | number;
    tick_rate_hz: number;
    time_origin_ms: number;
    render_spec: Record<string, unknown>;
};

export type SubscribedPayload = {
    stream_id: string;
    effective_stream: "LIVE";
    effective_channels: EnqueteurChannel[];
    effective_diff_policy: EnqueteurDiffPolicy;
    effective_snapshot_policy: EnqueteurSnapshotPolicy;
    effective_compression: EnqueteurCompressionPolicy;
};

export type FullSnapshotPayload = {
    schema_version: string;
    tick: number;
    step_hash: string;
    state: {
        world?: Record<string, unknown>;
        npcs?: Record<string, unknown>;
        investigation?: Record<string, unknown>;
        dialogue?: Record<string, unknown>;
        learning?: Record<string, unknown>;
        resolution?: Record<string, unknown>;
    };
};

export type FrameDiffPayload = {
    schema_version: string;
    from_tick: number;
    to_tick: number;
    prev_step_hash: string;
    step_hash: string;
    ops: Record<string, unknown>[];
};

export type CommandAcceptedPayload = {
    client_cmd_id: string;
};

export type CommandRejectedPayload = {
    client_cmd_id: string;
    reason_code: string;
    message: string;
};

export type WarnPayload = {
    code: string;
    message: string;
};

export type ErrorPayload = {
    code: string;
    message: string;
    fatal: boolean;
};

export type PongPayload = {
    nonce?: string | number | null;
};

export type KvpEnvelope<TMsgType extends string, TPayload> = {
    kvp_version: KvpVersion;
    msg_type: TMsgType;
    msg_id: string;
    sent_at_ms: number;
    payload: TPayload;
};

export type EnqueteurOutboundMsgType =
    | "VIEWER_HELLO"
    | "SUBSCRIBE"
    | "INPUT_COMMAND"
    | "PING";

export type EnqueteurInboundMsgType =
    | "KERNEL_HELLO"
    | "SUBSCRIBED"
    | "FULL_SNAPSHOT"
    | "FRAME_DIFF"
    | "COMMAND_ACCEPTED"
    | "COMMAND_REJECTED"
    | "WARN"
    | "ERROR"
    | "PONG";

export type EnqueteurOutboundPayloadByType = {
    VIEWER_HELLO: ViewerHelloPayload;
    SUBSCRIBE: SubscribePayload;
    INPUT_COMMAND: InputCommandPayload;
    PING: { nonce?: string | number | null };
};

export type EnqueteurInboundPayloadByType = {
    KERNEL_HELLO: KernelHelloPayload;
    SUBSCRIBED: SubscribedPayload;
    FULL_SNAPSHOT: FullSnapshotPayload;
    FRAME_DIFF: FrameDiffPayload;
    COMMAND_ACCEPTED: CommandAcceptedPayload;
    COMMAND_REJECTED: CommandRejectedPayload;
    WARN: WarnPayload;
    ERROR: ErrorPayload;
    PONG: PongPayload;
};

export type EnqueteurOutboundEnvelopeByType = {
    [K in EnqueteurOutboundMsgType]: KvpEnvelope<K, EnqueteurOutboundPayloadByType[K]>;
};

export type EnqueteurInboundEnvelopeByType = {
    [K in EnqueteurInboundMsgType]: KvpEnvelope<K, EnqueteurInboundPayloadByType[K]>;
};

export type EnqueteurOutboundEnvelope =
    EnqueteurOutboundEnvelopeByType[EnqueteurOutboundMsgType];

export type EnqueteurInboundEnvelope =
    EnqueteurInboundEnvelopeByType[EnqueteurInboundMsgType];

export type EnqueteurLiveProtocolErrorCode =
    | "NON_TEXT_FRAME"
    | "INVALID_JSON"
    | "INVALID_ENVELOPE"
    | "UNSUPPORTED_KVP_VERSION"
    | "UNKNOWN_MSG_TYPE"
    | "INVALID_PAYLOAD"
    | "UNEXPECTED_KERNEL_IDENTITY";

export class EnqueteurLiveProtocolError extends Error {
    readonly code: EnqueteurLiveProtocolErrorCode;
    readonly rawData?: unknown;

    constructor(
        code: EnqueteurLiveProtocolErrorCode,
        message: string,
        opts: { rawData?: unknown } = {}
    ) {
        super(message);
        this.name = "EnqueteurLiveProtocolError";
        this.code = code;
        this.rawData = opts.rawData;
    }
}

export type EnqueteurLiveClientWebSocket = {
    readonly readyState: number;
    onopen: ((event: Event) => void) | null;
    onclose: ((event: CloseEvent) => void) | null;
    onerror: ((event: Event) => void) | null;
    onmessage: ((event: MessageEvent<unknown>) => void) | null;
    send: (data: string) => void;
    close: (code?: number, reason?: string) => void;
};

export type EnqueteurLiveClientOpts = {
    url: string;
    viewerName?: string;
    viewerVersion?: string;
    supportedSchemaVersions?: readonly string[];
    supports?: Partial<ViewerHelloPayload["supports"]>;
    autoSendViewerHello?: boolean;
    expectedEngineName?: string;
    expectedSchemaVersion?: string;
    disconnectOnProtocolError?: boolean;
    websocketFactory?: (url: string) => EnqueteurLiveClientWebSocket;
};

type MessageHandler<T extends EnqueteurInboundMsgType> = (
    envelope: EnqueteurInboundEnvelopeByType[T]
) => void;

type OpenHandler = () => void;
type CloseHandler = (event: CloseEvent) => void;
type TransportErrorHandler = (event: Event) => void;
type ProtocolErrorHandler = (error: EnqueteurLiveProtocolError) => void;

const WS_CONNECTING = 0;
const WS_OPEN = 1;
const WS_CLOSING = 2;

const INBOUND_MESSAGE_TYPES: readonly EnqueteurInboundMsgType[] = [
    "KERNEL_HELLO",
    "SUBSCRIBED",
    "FULL_SNAPSHOT",
    "FRAME_DIFF",
    "COMMAND_ACCEPTED",
    "COMMAND_REJECTED",
    "WARN",
    "ERROR",
    "PONG",
];

const DEFAULT_SUBSCRIBE_CHANNELS: EnqueteurChannel[] = [
    "WORLD",
    "NPCS",
    "INVESTIGATION",
    "DIALOGUE",
    "LEARNING",
    "EVENTS",
];

const DEFAULT_VIEWER_SUPPORTS: ViewerHelloPayload["supports"] = {
    diff_stream: true,
    full_snapshot: true,
    replay_seek: false,
};

export class EnqueteurLiveClient {
    private readonly opts: Required<
        Pick<
            EnqueteurLiveClientOpts,
            | "url"
            | "viewerName"
            | "viewerVersion"
            | "autoSendViewerHello"
            | "expectedEngineName"
            | "expectedSchemaVersion"
            | "disconnectOnProtocolError"
        >
    > & {
        supportedSchemaVersions: string[];
        supports: ViewerHelloPayload["supports"];
        websocketFactory: (url: string) => EnqueteurLiveClientWebSocket;
    };

    private socket: EnqueteurLiveClientWebSocket | null = null;
    private readonly messageHandlers = new Map<
        EnqueteurInboundMsgType,
        Set<(envelope: EnqueteurInboundEnvelope) => void>
    >();
    private readonly openHandlers = new Set<OpenHandler>();
    private readonly closeHandlers = new Set<CloseHandler>();
    private readonly transportErrorHandlers = new Set<TransportErrorHandler>();
    private readonly protocolErrorHandlers = new Set<ProtocolErrorHandler>();

    constructor(opts: EnqueteurLiveClientOpts) {
        this.opts = {
            url: opts.url,
            viewerName: opts.viewerName ?? "enqueteur-webview",
            viewerVersion: opts.viewerVersion ?? "0.1.0",
            autoSendViewerHello: opts.autoSendViewerHello ?? true,
            expectedEngineName: opts.expectedEngineName ?? ENQUETEUR_ENGINE_NAME,
            expectedSchemaVersion: opts.expectedSchemaVersion ?? ENQUETEUR_SCHEMA_VERSION,
            disconnectOnProtocolError: opts.disconnectOnProtocolError ?? true,
            supportedSchemaVersions: normalizeSupportedSchemaVersions(
                opts.supportedSchemaVersions
            ),
            supports: {
                ...DEFAULT_VIEWER_SUPPORTS,
                ...opts.supports,
            },
            websocketFactory: opts.websocketFactory ?? defaultWebSocketFactory,
        };
    }

    connect(): void {
        this.disconnect();
        const ws = this.opts.websocketFactory(this.opts.url);
        this.socket = ws;

        ws.onopen = () => {
            this.emitOpen();
            if (this.opts.autoSendViewerHello) {
                this.sendViewerHello();
            }
        };

        ws.onclose = (event) => {
            if (this.socket === ws) {
                this.socket = null;
            }
            this.emitClose(event);
        };

        ws.onerror = (event) => {
            this.emitTransportError(event);
        };

        ws.onmessage = (event) => {
            this.onRawMessage(event.data);
        };
    }

    disconnect(code?: number, reason?: string): void {
        const ws = this.socket;
        this.socket = null;
        if (!ws) return;
        if (ws.readyState === WS_CONNECTING || ws.readyState === WS_OPEN) {
            ws.close(code, reason);
        } else if (ws.readyState === WS_CLOSING) {
            ws.close();
        }
    }

    isConnected(): boolean {
        return this.socket?.readyState === WS_OPEN;
    }

    onOpen(handler: OpenHandler): () => void {
        this.openHandlers.add(handler);
        return () => this.openHandlers.delete(handler);
    }

    onClose(handler: CloseHandler): () => void {
        this.closeHandlers.add(handler);
        return () => this.closeHandlers.delete(handler);
    }

    onTransportError(handler: TransportErrorHandler): () => void {
        this.transportErrorHandlers.add(handler);
        return () => this.transportErrorHandlers.delete(handler);
    }

    onProtocolError(handler: ProtocolErrorHandler): () => void {
        this.protocolErrorHandlers.add(handler);
        return () => this.protocolErrorHandlers.delete(handler);
    }

    onMessage<T extends EnqueteurInboundMsgType>(
        msgType: T,
        handler: MessageHandler<T>
    ): () => void {
        const bucket = this.getOrCreateMessageHandlerBucket(msgType);
        const adaptedHandler = handler as (envelope: EnqueteurInboundEnvelope) => void;
        bucket.add(adaptedHandler);
        return () => {
            bucket.delete(adaptedHandler);
        };
    }

    sendViewerHello(): boolean {
        return this.sendEnvelope("VIEWER_HELLO", {
            viewer_name: this.opts.viewerName,
            viewer_version: this.opts.viewerVersion,
            supported_schema_versions: [...this.opts.supportedSchemaVersions],
            supports: { ...this.opts.supports },
        });
    }

    sendSubscribe(payload: Partial<SubscribePayload> = {}): boolean {
        const channels = dedupeChannels(payload.channels ?? DEFAULT_SUBSCRIBE_CHANNELS);
        const effectivePayload: SubscribePayload = {
            stream: "LIVE",
            channels,
            diff_policy: payload.diff_policy ?? "DIFF_ONLY",
            snapshot_policy: payload.snapshot_policy ?? "ON_JOIN",
            compression: payload.compression ?? "NONE",
        };
        return this.sendEnvelope("SUBSCRIBE", effectivePayload);
    }

    sendInputCommand(payload: InputCommandPayload): boolean {
        return this.sendEnvelope("INPUT_COMMAND", payload);
    }

    sendPing(nonce?: string | number | null): boolean {
        return this.sendEnvelope("PING", { nonce });
    }

    sendEnvelope<T extends EnqueteurOutboundMsgType>(
        msgType: T,
        payload: EnqueteurOutboundPayloadByType[T]
    ): boolean {
        const ws = this.socket;
        if (!ws || ws.readyState !== WS_OPEN) {
            return false;
        }
        const envelope: KvpEnvelope<T, EnqueteurOutboundPayloadByType[T]> = {
            kvp_version: KVP_VERSION,
            msg_type: msgType,
            msg_id: safeUuid(),
            sent_at_ms: Date.now(),
            payload,
        };
        ws.send(JSON.stringify(envelope));
        return true;
    }

    private onRawMessage(rawData: unknown): void {
        try {
            const envelope = parseEnqueteurInboundEnvelope(rawData);
            if (envelope.msg_type === "KERNEL_HELLO") {
                this.validateKernelHelloIdentity(envelope.payload);
            }
            this.emitMessage(envelope);
        } catch (err) {
            const protocolError = toProtocolError(err, rawData);
            this.emitProtocolError(protocolError);
            if (this.opts.disconnectOnProtocolError) {
                this.disconnect();
            }
        }
    }

    private validateKernelHelloIdentity(payload: KernelHelloPayload): void {
        if (payload.engine_name !== this.opts.expectedEngineName) {
            throw new EnqueteurLiveProtocolError(
                "UNEXPECTED_KERNEL_IDENTITY",
                `Expected KERNEL_HELLO.engine_name=${this.opts.expectedEngineName}, got ${payload.engine_name}.`
            );
        }
        if (payload.schema_version !== this.opts.expectedSchemaVersion) {
            throw new EnqueteurLiveProtocolError(
                "UNEXPECTED_KERNEL_IDENTITY",
                `Expected KERNEL_HELLO.schema_version=${this.opts.expectedSchemaVersion}, got ${payload.schema_version}.`
            );
        }
    }

    private getOrCreateMessageHandlerBucket(
        msgType: EnqueteurInboundMsgType
    ): Set<(envelope: EnqueteurInboundEnvelope) => void> {
        const existing = this.messageHandlers.get(msgType);
        if (existing) return existing;
        const created = new Set<(envelope: EnqueteurInboundEnvelope) => void>();
        this.messageHandlers.set(msgType, created);
        return created;
    }

    private emitOpen(): void {
        for (const handler of this.openHandlers) handler();
    }

    private emitClose(event: CloseEvent): void {
        for (const handler of this.closeHandlers) handler(event);
    }

    private emitTransportError(event: Event): void {
        for (const handler of this.transportErrorHandlers) handler(event);
    }

    private emitProtocolError(error: EnqueteurLiveProtocolError): void {
        for (const handler of this.protocolErrorHandlers) handler(error);
    }

    private emitMessage(envelope: EnqueteurInboundEnvelope): void {
        const handlers = this.messageHandlers.get(envelope.msg_type);
        if (!handlers) return;
        for (const handler of handlers) {
            handler(envelope);
        }
    }
}

export function parseEnqueteurInboundEnvelope(
    rawData: unknown
): EnqueteurInboundEnvelope {
    if (typeof rawData !== "string") {
        throw new EnqueteurLiveProtocolError(
            "NON_TEXT_FRAME",
            "Inbound websocket frame must be a UTF-8 JSON text frame.",
            { rawData }
        );
    }

    let parsed: unknown;
    try {
        parsed = JSON.parse(rawData);
    } catch {
        throw new EnqueteurLiveProtocolError(
            "INVALID_JSON",
            "Inbound websocket frame is not valid JSON text.",
            { rawData }
        );
    }

    const record = asRecord(parsed, "envelope");
    const kvpVersion = requireString(record.kvp_version, "kvp_version");
    if (kvpVersion !== KVP_VERSION) {
        throw new EnqueteurLiveProtocolError(
            "UNSUPPORTED_KVP_VERSION",
            `Unsupported kvp_version '${kvpVersion}'.`
        );
    }

    const msgTypeRaw = requireString(record.msg_type, "msg_type");
    if (!isKnownInboundMsgType(msgTypeRaw)) {
        throw new EnqueteurLiveProtocolError(
            "UNKNOWN_MSG_TYPE",
            `Unsupported inbound msg_type '${msgTypeRaw}'.`
        );
    }

    const msgId = requireString(record.msg_id, "msg_id");
    const sentAtMs = requireNonNegativeInteger(record.sent_at_ms, "sent_at_ms");
    const payloadRecord = asRecord(record.payload, "payload");

    return parseInboundPayloadByType({
        msgType: msgTypeRaw,
        msgId,
        sentAtMs,
        payloadRecord,
    });
}

function parseInboundPayloadByType(args: {
    msgType: EnqueteurInboundMsgType;
    msgId: string;
    sentAtMs: number;
    payloadRecord: Record<string, unknown>;
}): EnqueteurInboundEnvelope {
    const {
        msgType,
        msgId,
        sentAtMs,
        payloadRecord,
    } = args;
    switch (msgType) {
        case "KERNEL_HELLO":
            return {
                kvp_version: KVP_VERSION,
                msg_type: msgType,
                msg_id: msgId,
                sent_at_ms: sentAtMs,
                payload: parseKernelHelloPayload(payloadRecord),
            };
        case "SUBSCRIBED":
            return {
                kvp_version: KVP_VERSION,
                msg_type: msgType,
                msg_id: msgId,
                sent_at_ms: sentAtMs,
                payload: parseSubscribedPayload(payloadRecord),
            };
        case "FULL_SNAPSHOT":
            return {
                kvp_version: KVP_VERSION,
                msg_type: msgType,
                msg_id: msgId,
                sent_at_ms: sentAtMs,
                payload: parseFullSnapshotPayload(payloadRecord),
            };
        case "FRAME_DIFF":
            return {
                kvp_version: KVP_VERSION,
                msg_type: msgType,
                msg_id: msgId,
                sent_at_ms: sentAtMs,
                payload: parseFrameDiffPayload(payloadRecord),
            };
        case "COMMAND_ACCEPTED":
            return {
                kvp_version: KVP_VERSION,
                msg_type: msgType,
                msg_id: msgId,
                sent_at_ms: sentAtMs,
                payload: {
                    client_cmd_id: requireString(
                        payloadRecord.client_cmd_id,
                        "COMMAND_ACCEPTED.client_cmd_id"
                    ),
                },
            };
        case "COMMAND_REJECTED":
            return {
                kvp_version: KVP_VERSION,
                msg_type: msgType,
                msg_id: msgId,
                sent_at_ms: sentAtMs,
                payload: {
                    client_cmd_id: requireString(
                        payloadRecord.client_cmd_id,
                        "COMMAND_REJECTED.client_cmd_id"
                    ),
                    reason_code: requireString(
                        payloadRecord.reason_code,
                        "COMMAND_REJECTED.reason_code"
                    ),
                    message: requireString(payloadRecord.message, "COMMAND_REJECTED.message"),
                },
            };
        case "WARN":
            return {
                kvp_version: KVP_VERSION,
                msg_type: msgType,
                msg_id: msgId,
                sent_at_ms: sentAtMs,
                payload: {
                    code: requireString(payloadRecord.code, "WARN.code"),
                    message: requireString(payloadRecord.message, "WARN.message"),
                },
            };
        case "ERROR":
            return {
                kvp_version: KVP_VERSION,
                msg_type: msgType,
                msg_id: msgId,
                sent_at_ms: sentAtMs,
                payload: {
                    code: requireString(payloadRecord.code, "ERROR.code"),
                    message: requireString(payloadRecord.message, "ERROR.message"),
                    fatal: requireBoolean(payloadRecord.fatal, "ERROR.fatal"),
                },
            };
        case "PONG":
            return {
                kvp_version: KVP_VERSION,
                msg_type: msgType,
                msg_id: msgId,
                sent_at_ms: sentAtMs,
                payload: {
                    nonce: parseOptionalNonce(payloadRecord.nonce),
                },
            };
        default:
            return assertNever(msgType);
    }
}

function parseKernelHelloPayload(
    payloadRecord: Record<string, unknown>
): KernelHelloPayload {
    return {
        engine_name: requireString(payloadRecord.engine_name, "KERNEL_HELLO.engine_name"),
        engine_version: requireString(payloadRecord.engine_version, "KERNEL_HELLO.engine_version"),
        schema_version: requireString(payloadRecord.schema_version, "KERNEL_HELLO.schema_version"),
        world_id: requireString(payloadRecord.world_id, "KERNEL_HELLO.world_id"),
        run_id: requireString(payloadRecord.run_id, "KERNEL_HELLO.run_id"),
        seed: requireSeed(payloadRecord.seed, "KERNEL_HELLO.seed"),
        tick_rate_hz: requirePositiveInteger(payloadRecord.tick_rate_hz, "KERNEL_HELLO.tick_rate_hz"),
        time_origin_ms: requireNonNegativeInteger(payloadRecord.time_origin_ms, "KERNEL_HELLO.time_origin_ms"),
        render_spec: asRecord(payloadRecord.render_spec, "KERNEL_HELLO.render_spec"),
    };
}

function parseSubscribedPayload(
    payloadRecord: Record<string, unknown>
): SubscribedPayload {
    const stream = requireString(payloadRecord.effective_stream, "SUBSCRIBED.effective_stream");
    if (stream !== "LIVE") {
        throw new EnqueteurLiveProtocolError(
            "INVALID_PAYLOAD",
            `SUBSCRIBED.effective_stream must be LIVE, got ${stream}.`
        );
    }
    return {
        stream_id: requireString(payloadRecord.stream_id, "SUBSCRIBED.stream_id"),
        effective_stream: "LIVE",
        effective_channels: parseChannelArray(
            payloadRecord.effective_channels,
            "SUBSCRIBED.effective_channels"
        ),
        effective_diff_policy: parseDiffPolicy(
            payloadRecord.effective_diff_policy,
            "SUBSCRIBED.effective_diff_policy"
        ),
        effective_snapshot_policy: parseSnapshotPolicy(
            payloadRecord.effective_snapshot_policy,
            "SUBSCRIBED.effective_snapshot_policy"
        ),
        effective_compression: parseCompressionPolicy(
            payloadRecord.effective_compression,
            "SUBSCRIBED.effective_compression"
        ),
    };
}

function parseFullSnapshotPayload(
    payloadRecord: Record<string, unknown>
): FullSnapshotPayload {
    return {
        schema_version: requireString(payloadRecord.schema_version, "FULL_SNAPSHOT.schema_version"),
        tick: requireNonNegativeInteger(payloadRecord.tick, "FULL_SNAPSHOT.tick"),
        step_hash: requireString(payloadRecord.step_hash, "FULL_SNAPSHOT.step_hash"),
        state: asRecord(payloadRecord.state, "FULL_SNAPSHOT.state"),
    };
}

function parseFrameDiffPayload(
    payloadRecord: Record<string, unknown>
): FrameDiffPayload {
    return {
        schema_version: requireString(payloadRecord.schema_version, "FRAME_DIFF.schema_version"),
        from_tick: requireNonNegativeInteger(payloadRecord.from_tick, "FRAME_DIFF.from_tick"),
        to_tick: requireNonNegativeInteger(payloadRecord.to_tick, "FRAME_DIFF.to_tick"),
        prev_step_hash: requireString(payloadRecord.prev_step_hash, "FRAME_DIFF.prev_step_hash"),
        step_hash: requireString(payloadRecord.step_hash, "FRAME_DIFF.step_hash"),
        ops: requireObjectArray(payloadRecord.ops, "FRAME_DIFF.ops"),
    };
}

function normalizeSupportedSchemaVersions(value: readonly string[] | undefined): string[] {
    const schemas = value ? [...value] : [ENQUETEUR_SCHEMA_VERSION];
    const normalized = schemas.map((schema) => schema.trim()).filter(Boolean);
    if (normalized.length === 0) {
        return [ENQUETEUR_SCHEMA_VERSION];
    }
    return Array.from(new Set(normalized));
}

function dedupeChannels(channels: readonly EnqueteurChannel[]): EnqueteurChannel[] {
    return Array.from(new Set(channels));
}

function parseChannelArray(value: unknown, field: string): EnqueteurChannel[] {
    const values = requireStringArray(value, field);
    if (values.length === 0) {
        throw new EnqueteurLiveProtocolError(
            "INVALID_PAYLOAD",
            `${field} must be non-empty.`
        );
    }
    const channels = values.map((item) => parseChannel(item, field));
    return dedupeChannels(channels);
}

function parseChannel(value: string, field: string): EnqueteurChannel {
    switch (value) {
        case "WORLD":
        case "NPCS":
        case "INVESTIGATION":
        case "DIALOGUE":
        case "LEARNING":
        case "EVENTS":
        case "DEBUG":
            return value;
        default:
            throw new EnqueteurLiveProtocolError(
                "INVALID_PAYLOAD",
                `Unsupported channel '${value}' in ${field}.`
            );
    }
}

function parseDiffPolicy(value: unknown, field: string): EnqueteurDiffPolicy {
    const parsed = requireString(value, field);
    switch (parsed) {
        case "DIFF_ONLY":
        case "PERIODIC_SNAPSHOT":
        case "SNAPSHOT_ON_DESYNC":
            return parsed;
        default:
            throw new EnqueteurLiveProtocolError(
                "INVALID_PAYLOAD",
                `Unsupported diff policy '${parsed}' in ${field}.`
            );
    }
}

function parseSnapshotPolicy(value: unknown, field: string): EnqueteurSnapshotPolicy {
    const parsed = requireString(value, field);
    switch (parsed) {
        case "ON_JOIN":
        case "NEVER":
            return parsed;
        default:
            throw new EnqueteurLiveProtocolError(
                "INVALID_PAYLOAD",
                `Unsupported snapshot policy '${parsed}' in ${field}.`
            );
    }
}

function parseCompressionPolicy(
    value: unknown,
    field: string
): EnqueteurCompressionPolicy {
    const parsed = requireString(value, field);
    if (parsed !== "NONE") {
        throw new EnqueteurLiveProtocolError(
            "INVALID_PAYLOAD",
            `Unsupported compression policy '${parsed}' in ${field}.`
        );
    }
    return "NONE";
}

function parseOptionalNonce(value: unknown): string | number | null | undefined {
    if (value === undefined || value === null) {
        return value;
    }
    if (typeof value === "string" || typeof value === "number") {
        return value;
    }
    throw new EnqueteurLiveProtocolError(
        "INVALID_PAYLOAD",
        "PONG.nonce must be a string, number, null, or omitted."
    );
}

function defaultWebSocketFactory(url: string): EnqueteurLiveClientWebSocket {
    return new WebSocket(url);
}

function toProtocolError(
    err: unknown,
    rawData: unknown
): EnqueteurLiveProtocolError {
    if (err instanceof EnqueteurLiveProtocolError) {
        return err;
    }
    const message = err instanceof Error ? err.message : String(err);
    return new EnqueteurLiveProtocolError(
        "INVALID_ENVELOPE",
        `Failed to parse inbound KVP envelope: ${message}`,
        { rawData }
    );
}

function isKnownInboundMsgType(value: string): value is EnqueteurInboundMsgType {
    return (INBOUND_MESSAGE_TYPES as readonly string[]).includes(value);
}

function requireString(value: unknown, field: string): string {
    if (typeof value !== "string" || value.trim().length === 0) {
        throw new EnqueteurLiveProtocolError(
            "INVALID_ENVELOPE",
            `${field} must be a non-empty string.`
        );
    }
    return value;
}

function requireSeed(value: unknown, field: string): string | number {
    if (typeof value === "string" || typeof value === "number") {
        return value;
    }
    throw new EnqueteurLiveProtocolError(
        "INVALID_PAYLOAD",
        `${field} must be a string or number.`
    );
}

function requireNonNegativeInteger(value: unknown, field: string): number {
    if (!Number.isInteger(value) || Number(value) < 0) {
        throw new EnqueteurLiveProtocolError(
            "INVALID_ENVELOPE",
            `${field} must be a non-negative integer.`
        );
    }
    return Number(value);
}

function requirePositiveInteger(value: unknown, field: string): number {
    if (!Number.isInteger(value) || Number(value) <= 0) {
        throw new EnqueteurLiveProtocolError(
            "INVALID_PAYLOAD",
            `${field} must be a positive integer.`
        );
    }
    return Number(value);
}

function requireBoolean(value: unknown, field: string): boolean {
    if (typeof value !== "boolean") {
        throw new EnqueteurLiveProtocolError(
            "INVALID_PAYLOAD",
            `${field} must be a boolean.`
        );
    }
    return value;
}

function requireStringArray(value: unknown, field: string): string[] {
    if (!Array.isArray(value)) {
        throw new EnqueteurLiveProtocolError(
            "INVALID_PAYLOAD",
            `${field} must be an array of strings.`
        );
    }
    return value.map((item) => requireString(item, field));
}

function requireObjectArray(value: unknown, field: string): Record<string, unknown>[] {
    if (!Array.isArray(value)) {
        throw new EnqueteurLiveProtocolError(
            "INVALID_PAYLOAD",
            `${field} must be an array.`
        );
    }
    return value.map((item) => asRecord(item, field));
}

function asRecord(value: unknown, field: string): Record<string, unknown> {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
        throw new EnqueteurLiveProtocolError(
            "INVALID_ENVELOPE",
            `${field} must be an object.`
        );
    }
    return value as Record<string, unknown>;
}

function assertNever(value: never): never {
    throw new Error(`Unhandled value: ${String(value)}`);
}

function safeUuid(): string {
    const c = globalThis.crypto as Crypto | undefined;
    if (c?.randomUUID) return c.randomUUID();
    return `msg_${Date.now().toString(16)}_${Math.random().toString(16).slice(2)}`;
}
