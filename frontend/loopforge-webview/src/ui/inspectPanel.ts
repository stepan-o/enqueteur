// src/ui/inspectPanel.ts
import type { WorldStore, WorldState, KvpAgent, KvpObject, KvpRoom } from "../state/worldStore";

export type InspectSelection =
    | { kind: "room"; id: number }
    | { kind: "agent"; id: number }
    | { kind: "object"; id: number }
    | null;

export type InspectHandle = {
    root: HTMLElement;
    setSelection: (sel: InspectSelection) => void;
    clear: () => void;
    getSelection: () => InspectSelection;
};

export function mountInspectPanel(store: WorldStore): InspectHandle {
    const root = document.createElement("div");
    root.className = "inspect-root";

    const panel = document.createElement("div");
    panel.className = "inspect-panel";
    root.appendChild(panel);

    let selection: InspectSelection = null;
    let lastState: WorldState | null = null;

    const render = (): void => {
        if (!selection || !lastState) {
            panel.style.display = "none";
            panel.innerHTML = "";
            return;
        }
        panel.style.display = "block";
        panel.innerHTML = "";

        if (selection.kind === "room") {
            const room = lastState.rooms.get(selection.id);
            if (!room) return renderMissing("Room", selection.id);
            renderRoom(panel, room);
            return;
        }

        if (selection.kind === "agent") {
            const agent = lastState.agents.get(selection.id);
            if (!agent) return renderMissing("Agent", selection.id);
            renderAgent(panel, agent, lastState);
            return;
        }

        if (selection.kind === "object") {
            const obj = lastState.objects.get(selection.id);
            if (!obj) return renderMissing("Object", selection.id);
            renderObject(panel, obj, lastState);
            return;
        }
    };

    const renderMissing = (label: string, id: number): void => {
        const title = document.createElement("div");
        title.className = "inspect-title";
        title.textContent = `${label} ${id}`;
        panel.appendChild(title);
        const line = document.createElement("div");
        line.className = "inspect-line";
        line.textContent = "No data available.";
        panel.appendChild(line);
    };

    store.subscribe((s) => {
        lastState = s;
        render();
    });

    const setSelection = (sel: InspectSelection): void => {
        selection = sel;
        render();
    };

    const clear = (): void => {
        setSelection(null);
    };

    document.addEventListener("pointerdown", (ev) => {
        if (!selection) return;
        const target = ev.target as Node | null;
        if (!target) return;
        if (panel.contains(target)) return;
        clear();
    });

    return {
        root,
        setSelection,
        clear,
        getSelection: () => selection,
    };
}

function renderRoom(panel: HTMLElement, room: KvpRoom): void {
    const title = document.createElement("div");
    title.className = "inspect-title";
    title.textContent = room.label ?? `Room ${room.room_id}`;
    panel.appendChild(title);

    const lines: Array<[string, string]> = [
        ["Room", String(room.room_id)],
        ["Zone", room.zone ?? "unknown"],
        ["Level", room.level?.toString() ?? "0"],
        ["Kind", String(room.kind_code)],
        ["Tension", room.tension_tier ?? "none"],
        ["Occupants", String(room.occupants?.length ?? 0)],
    ];

    renderLines(panel, lines);
}

function renderAgent(panel: HTMLElement, agent: KvpAgent, state: WorldState): void {
    const title = document.createElement("div");
    title.className = "inspect-title";
    title.textContent = `Agent ${agent.agent_id}`;
    panel.appendChild(title);

    const roomLabel = state.rooms.get(agent.room_id)?.label ?? `Room ${agent.room_id}`;
    const activeObject = findObjectByOccupant(state, agent.agent_id);
    const context = activeObject
        ? `${activeObject.class_code} #${activeObject.object_id}`
        : "none";

    const lines: Array<[string, string]> = [
        ["Room", roomLabel],
        ["Role", String(agent.role_code)],
        ["Action", String(agent.action_state_code)],
        ["Generation", String(agent.generation)],
        ["Interacting", context],
    ];

    renderLines(panel, lines);
}

function renderObject(panel: HTMLElement, obj: KvpObject, state: WorldState): void {
    const title = document.createElement("div");
    title.className = "inspect-title";
    title.textContent = `${obj.class_code}`;
    panel.appendChild(title);

    const roomLabel = state.rooms.get(obj.room_id)?.label ?? `Room ${obj.room_id}`;
    const occupant = obj.occupant_agent_id ? state.agents.get(obj.occupant_agent_id) : null;
    const occupantLabel = occupant ? `Agent ${occupant.agent_id}` : "none";

    const lines: Array<[string, string]> = [
        ["Object", String(obj.object_id)],
        ["Room", roomLabel],
        ["Status", String(obj.status_code)],
        ["Durability", obj.durability.toFixed(2)],
        ["Efficiency", obj.efficiency.toFixed(2)],
        ["Occupant", occupantLabel],
        ["Ticks in state", String(obj.ticks_in_state)],
    ];

    renderLines(panel, lines);
}

function renderLines(panel: HTMLElement, lines: Array<[string, string]>): void {
    for (const [label, value] of lines) {
        const row = document.createElement("div");
        row.className = "inspect-line";
        row.innerHTML = `<span class="inspect-label">${label}</span><span class="inspect-value">${value}</span>`;
        panel.appendChild(row);
    }
}

function findObjectByOccupant(state: WorldState, agentId: number): KvpObject | null {
    for (const obj of state.objects.values()) {
        if (obj.occupant_agent_id === agentId) return obj;
    }
    return null;
}
