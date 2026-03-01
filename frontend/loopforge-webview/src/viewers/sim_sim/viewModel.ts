import type { SimSimEvent, SimSimPrompt, SimSimRoom, SimSimWorldMeta } from "./simSimStore";

export type SecurityDirectiveTone = "stable" | "watch" | "alert";
export type SecurityDirectiveAction = "hold" | "monitor" | "stabilize";
export type SecurityDirectiveClarityTreatment = "crisp" | "noisy";

export type SecurityDirectiveEffect = {
    icon: string;
    text: string;
};

export type SecurityDirectiveDisplay = {
    label: string;
    blurbLines: string[];
    effects: SecurityDirectiveEffect[];
    clarityTreatment: SecurityDirectiveClarityTreatment;
    clarityHint: string;
};

export type SecurityDirective = {
    lead: string;
    clarity: number;
    tone: SecurityDirectiveTone;
    action: SecurityDirectiveAction;
    headline: string;
    summary: string;
    stamp: string;
    display: SecurityDirectiveDisplay;
};

export type ForecastBand = "low" | "mid" | "high" | "unknown";
export type ForecastSignal = "good" | "watch" | "bad" | "neutral";

export type ForecastMetric = {
    value: number | null;
    band: ForecastBand;
    signal: ForecastSignal;
};

export type ForecastRoomBands = {
    roomId: number;
    roomName: string;
    locked: boolean;
    securityClarity: number;
    throughput: ForecastMetric;
    incidentRisk: ForecastMetric;
    absenteeismRisk: ForecastMetric;
    orderIndex: ForecastMetric;
    overall: ForecastMetric;
};

export type EventRailSeverity = "minor" | "notable";

export type EventRailCard = {
    id: string;
    source: "event" | "prompt";
    tick: number;
    stamp: string;
    severity: EventRailSeverity;
    title: string;
    subtitle: string;
    details: string;
    roomId: number | null;
    roomName: string | null;
    supervisorCode: string | null;
};

export type SpotlightPromptChoice = {
    id: string;
    label: string;
    recommended: boolean;
};

export type SpotlightPrompt = {
    promptId: string;
    kind: "critical" | "conflict";
    tickCreated: number;
    title: string;
    cinematicLead: string;
    body: string;
    choices: SpotlightPromptChoice[];
    roomId: number | null;
    supervisorCode: string | null;
};

export type RecapDeltas = {
    factory?: Partial<{
        stress: number;
        discipline: number;
        alignment: number;
        cash: number;
        output: number;
        accidents: number;
        casualties: number;
    }>;
    rooms?: Record<
        number,
        Partial<{
            stress: number;
            discipline: number;
            alignment: number;
            equipment_condition: number;
            output: number;
            casualties: number;
        }>
    >;
};

export type SupervisorChange = {
    code: string;
    fromRoom?: number | null;
    toRoom?: number | null;
    confidenceDelta?: number;
    loyaltyDelta?: number;
    influenceDelta?: number;
    cooldownDays?: number;
};

export type RecapTone = "positive" | "neutral" | "negative";

export type RecapPanel = {
    id: "control" | "operations" | "leadership";
    title: string;
    tone: RecapTone;
    stamp: string;
    lines: string[];
};

const LEAD_BASE_CLARITY: Record<string, number> = {
    L: 0.9,
    S: 0.72,
    W: 0.64,
    T: 0.48,
    C: 0.38,
};

const LEAD_DIRECTIVE_PRESETS: Record<
    string,
    {
        label: string;
        blurb: string;
        effects: SecurityDirectiveEffect[];
    }
> = {
    L: {
        label: "ORDER LOCK",
        blurb: "Lock sequence before throughput; deviations are frozen first.",
        effects: [
            { icon: "[LOCK]", text: "chain-of-command gates harden" },
            { icon: "[SEQ]", text: "step order checks tighten" },
            { icon: "[SYNC]", text: "cross-room timing is enforced" },
        ],
    },
    S: {
        label: "CONVEYOR PRIORITY",
        blurb: "Flow continuity outranks everything; stalls are resolved immediately.",
        effects: [
            { icon: "[BELT]", text: "jam-clearing gets first allocation" },
            { icon: "[REROUTE]", text: "queues auto-reroute around friction" },
            { icon: "[LOAD]", text: "handoff lanes get throughput bias" },
        ],
    },
    W: {
        label: "MATERIALS PRIORITY",
        blurb: "Feedstock quality and stock discipline dominate dispatch choices.",
        effects: [
            { icon: "[STOCK]", text: "inventory guard bands expand" },
            { icon: "[QA]", text: "input quality checks tighten" },
            { icon: "[PULL]", text: "replenishment follows pull demand" },
        ],
    },
    C: {
        label: "CHAOS DISPATCH",
        blurb: "Rapid opportunistic routing; standard queues may be bypassed.",
        effects: [
            { icon: "[BURST]", text: "burst redeployments become common" },
            { icon: "[RISK]", text: "high-variance gambits are tolerated" },
            { icon: "[OVR]", text: "local overrides outrank schedules" },
        ],
    },
    T: {
        label: "VIBE DISPATCH",
        blurb: "Crew sentiment and momentum weight routing in real time.",
        effects: [
            { icon: "[MORALE]", text: "morale-weighted assignment bias" },
            { icon: "[COOL]", text: "conflict cooldown buffers activate" },
            { icon: "[PULSE]", text: "rhythm-driven shift pivots increase" },
        ],
    },
};

const NOTABLE_EVENT_KINDS = new Set<string>([
    "critical_triggered",
    "critical_suppressed",
    "conflict_event",
    "conflict_discovered",
    "input_rejected",
]);

export function deriveSecurityDirective(
    securityLead: SimSimWorldMeta["security_lead"] | string | undefined,
    eventHistory: Iterable<SimSimEvent>
): SecurityDirective {
    const lead = normalizeLeadCode(securityLead);
    const events = toSortedEvents(eventHistory);
    const recent = events.slice(-12);

    let clarity = LEAD_BASE_CLARITY[lead] ?? 0.5;
    let criticalTriggered = 0;
    let criticalSuppressed = 0;
    let conflicts = 0;
    let rejections = 0;

    for (const event of recent) {
        switch (event.kind) {
            case "critical_triggered":
                criticalTriggered += 1;
                clarity -= 0.22;
                break;
            case "critical_suppressed":
                criticalSuppressed += 1;
                clarity += 0.16;
                break;
            case "conflict_event":
                conflicts += 1;
                clarity -= 0.1;
                break;
            case "conflict_discovered":
                conflicts += 1;
                clarity -= 0.06;
                break;
            case "security_redistribution":
                clarity += 0.05;
                break;
            case "assignment_resolved":
                clarity += 0.03;
                break;
            case "input_rejected":
                rejections += 1;
                clarity -= 0.08;
                break;
            case "tension_zone":
                clarity -= 0.06;
                break;
            default:
                break;
        }
    }
    if (recent.length > 0 && criticalTriggered === 0 && conflicts === 0 && rejections === 0) clarity += 0.04;
    clarity = clamp01(clarity);

    const tone: SecurityDirectiveTone = clarity >= 0.72 ? "stable" : clarity >= 0.45 ? "watch" : "alert";
    const action: SecurityDirectiveAction = tone === "stable" ? "hold" : tone === "watch" ? "monitor" : "stabilize";
    const stamp = buildTickStamp(events);
    const display = deriveSecurityDirectiveDisplay(lead, clarity, tone, action);

    const headline =
        tone === "stable"
            ? `Security net is coherent under ${lead}.`
            : tone === "watch"
              ? `Security posture under ${lead} needs tighter watch.`
              : `Security command under ${lead} is fragmented.`;

    const summary = [
        `clarity ${toPct(clarity)}`,
        `critical ${criticalTriggered}/${criticalSuppressed}`,
        `conflicts ${conflicts}`,
        `rejections ${rejections}`,
    ].join(" | ");

    return {
        lead,
        clarity: round3(clarity),
        tone,
        action,
        headline,
        summary,
        stamp,
        display,
    };
}

export function deriveForecastBandsPerRoom(
    roomsInput: Iterable<SimSimRoom>,
    securityDirectiveOrClarity: SecurityDirective | number
): ForecastRoomBands[] {
    const securityClarity =
        typeof securityDirectiveOrClarity === "number"
            ? clamp01(securityDirectiveOrClarity)
            : clamp01(securityDirectiveOrClarity.clarity);

    const rooms = Array.from(roomsInput).sort((a, b) => a.room_id - b.room_id);
    return rooms.map((room) => {
        if (
            room.locked ||
            room.stress === null ||
            room.discipline === null ||
            room.alignment === null ||
            room.equipment_condition === null
        ) {
            return {
                roomId: room.room_id,
                roomName: room.name,
                locked: room.locked,
                securityClarity: round3(securityClarity),
                throughput: unknownMetric(),
                incidentRisk: unknownMetric(),
                absenteeismRisk: unknownMetric(),
                orderIndex: unknownMetric(),
                overall: unknownMetric(),
            };
        }

        const stress = clamp01(room.stress);
        const discipline = clamp01(room.discipline);
        const alignment = clamp01(room.alignment);
        const equipment = clamp01(room.equipment_condition);

        // v1 heuristics mirror current backend formula families (absenteeism/accident/productivity).
        const absenteeism = clamp01(0.05 + (0.35 * stress) - (0.25 * discipline));
        const incidentRisk = clamp01(0.02 + (0.25 * (1 - discipline)) + (0.25 * stress) + (0.3 * (1 - equipment)) + ((1 - securityClarity) * 0.08));
        const productivity = clamp01(0.5 + (0.7 * discipline) - (0.3 * stress));
        const throughput = clamp01(productivity * (1 - absenteeism) * equipment * (0.85 + (0.15 * securityClarity)));
        const orderIndex = clamp01(((discipline * 0.6) + (alignment * 0.4)) * securityClarity + ((1 - securityClarity) * 0.2));
        const overallScore = clamp01((throughput * 0.45) + ((1 - incidentRisk) * 0.3) + (orderIndex * 0.25));

        return {
            roomId: room.room_id,
            roomName: room.name,
            locked: false,
            securityClarity: round3(securityClarity),
            throughput: metricPositive(throughput),
            incidentRisk: metricRisk(incidentRisk),
            absenteeismRisk: metricRisk(absenteeism),
            orderIndex: metricPositive(orderIndex),
            overall: metricPositive(overallScore),
        };
    });
}

export function deriveEventRailCards(
    eventsInput: Iterable<SimSimEvent>,
    roomsInput: Iterable<SimSimRoom>,
    promptsInput: Iterable<SimSimPrompt>
): EventRailCard[] {
    const rooms = Array.from(roomsInput);
    const roomById = new Map<number, string>(rooms.map((room) => [room.room_id, room.name]));
    const prompts = toSortedPrompts(promptsInput);
    const events = toSortedEvents(eventsInput);

    const eventCards = events.map((event) => {
        const severity = classifyEventSeverity(event);
        const roomName = typeof event.room_id === "number" ? (roomById.get(event.room_id) ?? null) : null;
        return {
            id: `e:${event.tick}:${event.event_id}`,
            source: "event" as const,
            tick: event.tick,
            stamp: `T${pad2(event.tick)} · #${event.event_id}`,
            severity,
            title: humanizeToken(event.kind),
            subtitle: buildEventSubtitle(event, roomName),
            details: summarizeEventDetails(event.details),
            roomId: typeof event.room_id === "number" ? event.room_id : null,
            roomName,
            supervisorCode: typeof event.supervisor === "string" ? event.supervisor : null,
        };
    });

    const pendingPromptCards = prompts
        .filter((prompt) => prompt.status !== "resolved")
        .map((prompt) => {
            const kindToken = String(prompt.kind || "").toLowerCase();
            const notable = kindToken === "critical" || kindToken === "conflict";
            return {
                id: `p:${prompt.tick_created}:${prompt.prompt_id}`,
                source: "prompt" as const,
                tick: prompt.tick_created,
                stamp: `T${pad2(prompt.tick_created)} · ${prompt.prompt_id}`,
                severity: notable ? ("notable" as const) : ("minor" as const),
                title: `Pending ${humanizeToken(prompt.kind)} decision`,
                subtitle: `choices=${prompt.choices.length} · status=${prompt.status}`,
                details: prompt.selected_choice ? `selected=${prompt.selected_choice}` : "awaiting selection",
                roomId: promptRoomId(prompt.payload),
                roomName: roomById.get(promptRoomId(prompt.payload) ?? -1) ?? null,
                supervisorCode: promptSupervisorCode(prompt.payload),
            };
        });

    return [...eventCards, ...pendingPromptCards].sort((a, b) => {
        if (a.tick !== b.tick) return a.tick - b.tick;
        if (a.source !== b.source) return a.source === "event" ? -1 : 1;
        return a.id.localeCompare(b.id);
    });
}

export function deriveSpotlightPrompt(promptsInput: Iterable<SimSimPrompt>): SpotlightPrompt | null {
    const prompts = toSortedPrompts(promptsInput).filter((prompt) => {
        const kind = String(prompt.kind || "").toLowerCase();
        return prompt.status !== "resolved" && (kind === "critical" || kind === "conflict");
    });
    if (prompts.length === 0) return null;

    const selected = [...prompts].sort((a, b) => {
        const ap = promptPriority(a.kind);
        const bp = promptPriority(b.kind);
        if (ap !== bp) return ap - bp;
        if (a.tick_created !== b.tick_created) return a.tick_created - b.tick_created;
        return a.prompt_id.localeCompare(b.prompt_id);
    })[0];

    const kind = String(selected.kind).toLowerCase() === "critical" ? "critical" : "conflict";
    const roomId = promptRoomId(selected.payload);
    const supervisorCode = promptSupervisorCode(selected.payload);
    const choices = selected.choices.map((choice) => ({
        id: choice,
        label: choiceLabel(kind, choice),
        recommended: isRecommendedChoice(kind, choice),
    }));

    if (kind === "critical") {
        const sup = supervisorCode ?? "unknown";
        const room = roomId === null ? "unknown room" : `room ${roomId}`;
        return {
            promptId: selected.prompt_id,
            kind,
            tickCreated: selected.tick_created,
            title: `Critical escalation: ${sup}`,
            cinematicLead: "A high-confidence supervisor is pushing an irreversible move.",
            body: `Evaluate intervention at ${room}. Suppress to stabilize, or allow to commit the critical event path.`,
            choices,
            roomId,
            supervisorCode,
        };
    }

    const pairToken = promptPairLabel(selected.payload);
    return {
        promptId: selected.prompt_id,
        kind,
        tickCreated: selected.tick_created,
        title: `Conflict hearing: ${pairToken}`,
        cinematicLead: "A hostile supervisor edge demands resolution.",
        body: "Support a side to shift confidence and influence, or suppress to de-escalate the clash.",
        choices,
        roomId,
        supervisorCode,
    };
}

export function deriveRecapPanels(
    day: number,
    eventsInput: Iterable<SimSimEvent>,
    deltas: RecapDeltas,
    supervisorChanges: Iterable<SupervisorChange>
): RecapPanel[] {
    const events = toSortedEvents(eventsInput);
    const changes = Array.from(supervisorChanges).sort((a, b) => a.code.localeCompare(b.code));
    const factory = deltas.factory ?? {};
    const roomDeltas = deltas.rooms ?? {};

    const criticalTriggered = events.filter((event) => event.kind === "critical_triggered").length;
    const criticalSuppressed = events.filter((event) => event.kind === "critical_suppressed").length;
    const conflicts = events.filter((event) => event.kind === "conflict_event").length;
    const rejectedInputs = events.filter((event) => event.kind === "input_rejected").length;
    const casualtySignal = events.reduce((total, event) => total + extractEventCasualtySignal(event), 0);

    const controlScore =
        numberOrZero(factory.discipline) -
        numberOrZero(factory.stress) +
        (criticalSuppressed * 0.08) -
        (criticalTriggered * 0.12) -
        (conflicts * 0.05) -
        (rejectedInputs * 0.03);
    const controlTone: RecapTone = controlScore >= 0.08 ? "positive" : controlScore <= -0.08 ? "negative" : "neutral";

    const controlLines = [
        `security events: critical ${criticalTriggered}/${criticalSuppressed} (triggered/suppressed), conflicts ${conflicts}, input rejections ${rejectedInputs}`,
        `factory deltas: stress ${fmtDeltaPct(factory.stress)}, discipline ${fmtDeltaPct(factory.discipline)}, alignment ${fmtDeltaPct(factory.alignment)}`,
        `casualty signal: ${casualtySignal.toFixed(2)}`,
    ];

    const roomRows = Object.entries(roomDeltas)
        .map(([roomId, row]) => {
            const impact = Math.abs(numberOrZero(row.stress)) + Math.abs(numberOrZero(row.discipline)) + Math.abs(numberOrZero(row.equipment_condition));
            return { roomId: Number(roomId), row, impact };
        })
        .filter((item) => Number.isFinite(item.roomId))
        .sort((a, b) => (b.impact - a.impact) || (a.roomId - b.roomId));

    const operationsLines =
        roomRows.length === 0
            ? ["no projected room deltas supplied"]
            : roomRows.slice(0, 3).map((item) => {
                  const row = item.row;
                  return [
                      `room ${item.roomId}:`,
                      `stress ${fmtDeltaPct(row.stress)},`,
                      `discipline ${fmtDeltaPct(row.discipline)},`,
                      `alignment ${fmtDeltaPct(row.alignment)},`,
                      `equipment ${fmtDeltaPct(row.equipment_condition)}`,
                  ].join(" ");
              });

    const operationsBias =
        roomRows.reduce((acc, item) => acc + numberOrZero(item.row.discipline) - numberOrZero(item.row.stress), 0) -
        roomRows.reduce((acc, item) => acc + numberOrZero(item.row.equipment_condition), 0) * 0.25;
    const operationsTone: RecapTone = operationsBias >= 0.1 ? "positive" : operationsBias <= -0.1 ? "negative" : "neutral";

    const leadershipLines =
        changes.length === 0
            ? ["no supervisor movement or deltas supplied"]
            : changes.map((change) =>
                  [
                      `${change.code}:`,
                      `${fmtRoomMove(change.fromRoom)} -> ${fmtRoomMove(change.toRoom)}`,
                      `conf ${fmtSigned(change.confidenceDelta)}`,
                      `loyalty ${fmtSigned(change.loyaltyDelta)}`,
                      `influence ${fmtSigned(change.influenceDelta)}`,
                  ].join(" ")
              );

    const leadershipNet = changes.reduce(
        (acc, change) => acc + numberOrZero(change.confidenceDelta) + (numberOrZero(change.loyaltyDelta) * 0.5),
        0
    );
    const leadershipTone: RecapTone = leadershipNet >= 0.08 ? "positive" : leadershipNet <= -0.08 ? "negative" : "neutral";

    const stamp = `Day ${day}`;
    return [
        {
            id: "control",
            title: `Day ${day} Control`,
            tone: controlTone,
            stamp,
            lines: controlLines,
        },
        {
            id: "operations",
            title: `Day ${day} Operations`,
            tone: operationsTone,
            stamp,
            lines: operationsLines,
        },
        {
            id: "leadership",
            title: `Day ${day} Leadership`,
            tone: leadershipTone,
            stamp,
            lines: leadershipLines,
        },
    ];
}

export function runViewModelDevHarness(): {
    securityDirective: SecurityDirective;
    forecastBands: ForecastRoomBands[];
    eventRailCards: EventRailCard[];
    spotlightPrompt: SpotlightPrompt | null;
    recapPanels: RecapPanel[];
} {
    const worldMeta: SimSimWorldMeta = {
        day: 7,
        tick: 7,
        phase: "awaiting_prompts",
        time: "23:00",
        tick_hz: 1,
        seed: 7,
        run_id: "dev-harness",
        world_id: "world-dev",
        security_lead: "L",
    };

    const rooms: SimSimRoom[] = [
        {
            room_id: 1,
            name: "Security",
            unlocked_day: 0,
            locked: false,
            supervisor: "L",
            workers_assigned: { dumb: null, smart: null },
            workers_present: { dumb: null, smart: null },
            equipment_condition: 1,
            stress: null,
            discipline: null,
            alignment: null,
            output_today: {
                raw_brains_dumb: 0,
                raw_brains_smart: 0,
                washed_dumb: 0,
                washed_smart: 0,
                substrate_gallons: 0,
                ribbon_yards: 0,
            },
            accidents_today: { count: 0, casualties: 0 },
        },
        {
            room_id: 2,
            name: "Synaptic Lattice Forge",
            unlocked_day: 1,
            locked: false,
            supervisor: "S",
            workers_assigned: { dumb: 4, smart: 2 },
            workers_present: { dumb: 3, smart: 2 },
            equipment_condition: 0.82,
            stress: 0.36,
            discipline: 0.62,
            alignment: 0.51,
            output_today: {
                raw_brains_dumb: 12,
                raw_brains_smart: 8,
                washed_dumb: 0,
                washed_smart: 0,
                substrate_gallons: 0,
                ribbon_yards: 0,
            },
            accidents_today: { count: 0, casualties: 0 },
        },
        {
            room_id: 3,
            name: "Burn-in Theatre",
            unlocked_day: 2,
            locked: false,
            supervisor: "C",
            workers_assigned: { dumb: 2, smart: 2 },
            workers_present: { dumb: 1, smart: 2 },
            equipment_condition: 0.67,
            stress: 0.58,
            discipline: 0.49,
            alignment: 0.42,
            output_today: {
                raw_brains_dumb: 6,
                raw_brains_smart: 4,
                washed_dumb: 2,
                washed_smart: 1,
                substrate_gallons: 0,
                ribbon_yards: 0,
            },
            accidents_today: { count: 1, casualties: 0 },
        },
    ];

    const events: SimSimEvent[] = [
        { tick: 7, event_id: 90, kind: "conflict_event", room_id: 2, supervisor: "L", details: { winner: "L", loser: "S" } },
        { tick: 7, event_id: 91, kind: "critical_triggered", supervisor: "S", details: { name: "Conveyor Overdrive", casualties: 2 } },
        { tick: 7, event_id: 92, kind: "input_rejected", details: { reason_code: "SUPERVISOR_SWAP_BUDGET_EXCEEDED", reason: "daily cap reached" } },
    ];

    const prompts: SimSimPrompt[] = [
        {
            prompt_id: "prompt_critical_7_S",
            kind: "critical",
            tick_created: 7,
            choices: ["allow", "suppress"],
            status: "pending",
            selected_choice: null,
            payload: { supervisor: "S", room_id: 2 },
        },
    ];

    const securityDirective = deriveSecurityDirective(worldMeta.security_lead, events);
    const forecastBands = deriveForecastBandsPerRoom(rooms, securityDirective);
    const eventRailCards = deriveEventRailCards(events, rooms, prompts);
    const spotlightPrompt = deriveSpotlightPrompt(prompts);
    const recapPanels = deriveRecapPanels(
        worldMeta.day,
        events,
        {
            factory: { stress: 0.06, discipline: -0.04, alignment: -0.02 },
            rooms: {
                2: { stress: 0.03, discipline: -0.01, equipment_condition: -0.06 },
                3: { stress: 0.08, discipline: -0.03, equipment_condition: -0.1 },
            },
        },
        [
            { code: "L", fromRoom: 1, toRoom: 1, confidenceDelta: 0.1, loyaltyDelta: 0.03, influenceDelta: 0.05 },
            { code: "S", fromRoom: 2, toRoom: 2, confidenceDelta: -0.15, loyaltyDelta: -0.05, influenceDelta: -0.08 },
        ]
    );

    const derived = {
        securityDirective,
        forecastBands,
        eventRailCards,
        spotlightPrompt,
        recapPanels,
    };
    console.info("[sim_sim:viewModel harness] derived", derived);
    return derived;
}

function toSortedEvents(eventsInput: Iterable<SimSimEvent>): SimSimEvent[] {
    return Array.from(eventsInput).sort((a, b) => (a.tick - b.tick) || (a.event_id - b.event_id));
}

function toSortedPrompts(promptsInput: Iterable<SimSimPrompt>): SimSimPrompt[] {
    return Array.from(promptsInput).sort((a, b) => (a.tick_created - b.tick_created) || a.prompt_id.localeCompare(b.prompt_id));
}

function normalizeLeadCode(raw: string | undefined): string {
    const token = (raw ?? "L").trim().toUpperCase();
    return token.length > 0 ? token : "L";
}

function deriveSecurityDirectiveDisplay(
    lead: string,
    clarity: number,
    tone: SecurityDirectiveTone,
    action: SecurityDirectiveAction
): SecurityDirectiveDisplay {
    const preset = LEAD_DIRECTIVE_PRESETS[lead] ?? LEAD_DIRECTIVE_PRESETS["L"];
    const treatment: SecurityDirectiveClarityTreatment = clarity >= 0.58 ? "crisp" : "noisy";
    const clarityHint = treatment === "crisp" ? "CRISP EDGE" : "NOISY EDGE";
    const toneLine =
        tone === "stable"
            ? `Signal stable: maintain ${action} posture.`
            : tone === "watch"
              ? `Signal drifting: escalate ${action} checkpoints.`
              : `Signal fractured: force ${action} under direct control.`;
    return {
        label: preset.label,
        blurbLines: [preset.blurb, toneLine],
        effects: preset.effects.slice(0, 4),
        clarityTreatment: treatment,
        clarityHint,
    };
}

function buildTickStamp(events: SimSimEvent[]): string {
    if (events.length === 0) return "T--";
    return `T${pad2(events[events.length - 1].tick)}`;
}

function clamp01(value: number): number {
    if (!Number.isFinite(value)) return 0;
    return Math.max(0, Math.min(1, value));
}

function round3(value: number): number {
    return Math.round(value * 1000) / 1000;
}

function toPct(value: number): string {
    return `${Math.round(clamp01(value) * 100)}%`;
}

function bandFromScore(value: number): ForecastBand {
    if (!Number.isFinite(value)) return "unknown";
    if (value < 0.34) return "low";
    if (value < 0.67) return "mid";
    return "high";
}

function metricPositive(value: number): ForecastMetric {
    const v = clamp01(value);
    const band = bandFromScore(v);
    return {
        value: round3(v),
        band,
        signal: band === "high" ? "good" : band === "mid" ? "watch" : "bad",
    };
}

function metricRisk(value: number): ForecastMetric {
    const v = clamp01(value);
    const band = bandFromScore(v);
    return {
        value: round3(v),
        band,
        signal: band === "high" ? "bad" : band === "mid" ? "watch" : "good",
    };
}

function unknownMetric(): ForecastMetric {
    return { value: null, band: "unknown", signal: "neutral" };
}

function classifyEventSeverity(event: SimSimEvent): EventRailSeverity {
    if (NOTABLE_EVENT_KINDS.has(event.kind)) return "notable";
    if (event.kind.includes("critical") || event.kind.includes("conflict")) return "notable";
    const casualties = extractEventCasualtySignal(event);
    if (casualties > 0) return "notable";
    const promptKind = detailString(event.details, "kind").toLowerCase();
    if (event.kind === "prompt_resolved" && (promptKind === "critical" || promptKind === "conflict")) return "notable";
    return "minor";
}

function buildEventSubtitle(event: SimSimEvent, roomName: string | null): string {
    const bits: string[] = [];
    if (roomName) bits.push(roomName);
    if (typeof event.supervisor === "string" && event.supervisor.length > 0) bits.push(`sup ${event.supervisor}`);
    if (bits.length === 0) return "factory-wide";
    return bits.join(" · ");
}

function summarizeEventDetails(details: Record<string, unknown> | undefined): string {
    if (!details) return "no details";
    const pairs = Object.entries(details)
        .sort(([a], [b]) => a.localeCompare(b))
        .slice(0, 4)
        .map(([key, value]) => `${key}=${detailValue(value)}`);
    return pairs.length > 0 ? pairs.join(", ") : "no details";
}

function detailValue(value: unknown): string {
    if (typeof value === "string") return value;
    if (typeof value === "number") return Number.isFinite(value) ? String(round3(value)) : "nan";
    if (typeof value === "boolean") return value ? "true" : "false";
    if (Array.isArray(value)) return `[${value.map(detailValue).join("|")}]`;
    if (value && typeof value === "object") return "{...}";
    return "null";
}

function detailString(details: Record<string, unknown> | undefined, key: string): string {
    if (!details) return "";
    const value = details[key];
    return typeof value === "string" ? value : "";
}

function promptRoomId(payload: Record<string, unknown> | undefined): number | null {
    if (!payload) return null;
    const direct = payload["room_id"];
    if (typeof direct === "number" && Number.isFinite(direct)) return direct;
    const roomPair = payload["room_pair"];
    if (Array.isArray(roomPair) && typeof roomPair[0] === "number" && Number.isFinite(roomPair[0])) return roomPair[0];
    return null;
}

function promptSupervisorCode(payload: Record<string, unknown> | undefined): string | null {
    if (!payload) return null;
    const sup = payload["supervisor"];
    if (typeof sup === "string" && sup.length > 0) return sup;
    const pair = payload["pair"];
    if (Array.isArray(pair) && typeof pair[0] === "string" && pair[0].length > 0) return pair[0];
    return null;
}

function promptPairLabel(payload: Record<string, unknown> | undefined): string {
    if (!payload) return "unknown pair";
    const pair = payload["pair"];
    if (Array.isArray(pair) && pair.length >= 2 && typeof pair[0] === "string" && typeof pair[1] === "string") {
        return `${pair[0]} vs ${pair[1]}`;
    }
    return "unknown pair";
}

function promptPriority(kind: string): number {
    const token = String(kind).toLowerCase();
    if (token === "critical") return 0;
    if (token === "conflict") return 1;
    return 2;
}

function choiceLabel(kind: "critical" | "conflict", choice: string): string {
    if (kind === "critical") {
        if (choice === "allow") return "Allow escalation";
        if (choice === "suppress") return "Suppress event";
    } else {
        if (choice === "support_A") return "Support side A";
        if (choice === "support_B") return "Support side B";
        if (choice === "suppress") return "Suppress conflict";
    }
    return humanizeToken(choice);
}

function isRecommendedChoice(kind: "critical" | "conflict", choice: string): boolean {
    if (kind === "critical") return choice === "suppress";
    return choice === "suppress";
}

function extractEventCasualtySignal(event: SimSimEvent): number {
    const details = event.details;
    if (!details) return 0;
    const direct = details["casualties"];
    if (typeof direct === "number" && Number.isFinite(direct)) return direct;
    const max = details["casualties_max"];
    if (typeof max === "number" && Number.isFinite(max)) return max * 0.5;
    const min = details["casualties_min"];
    if (typeof min === "number" && Number.isFinite(min)) return min * 0.5;
    return 0;
}

function fmtDeltaPct(value: number | undefined): string {
    if (!Number.isFinite(value ?? NaN)) return "n/a";
    const v = Number(value);
    const sign = v > 0 ? "+" : "";
    return `${sign}${Math.round(v * 1000) / 10}pp`;
}

function fmtSigned(value: number | undefined): string {
    if (!Number.isFinite(value ?? NaN)) return "n/a";
    const v = Number(value);
    const sign = v > 0 ? "+" : "";
    return `${sign}${round3(v)}`;
}

function fmtRoomMove(roomId: number | null | undefined): string {
    return Number.isFinite(roomId ?? NaN) ? `r${roomId}` : "none";
}

function numberOrZero(value: number | undefined): number {
    return Number.isFinite(value ?? NaN) ? Number(value) : 0;
}

function humanizeToken(token: string): string {
    const clean = String(token || "").trim().replace(/[_-]+/g, " ");
    if (!clean) return "Unknown";
    return clean
        .split(" ")
        .filter((part) => part.length > 0)
        .map((part) => part[0].toUpperCase() + part.slice(1))
        .join(" ");
}

function pad2(value: number): string {
    const n = Math.max(0, Math.floor(Math.abs(value)));
    return String(n).padStart(2, "0");
}
