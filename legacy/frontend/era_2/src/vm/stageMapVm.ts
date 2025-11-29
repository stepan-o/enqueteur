import type { EpisodeViewModel } from "./episodeVm";

export interface StageMapRoomVM {
  id: string; // e.g., "control_room"
  label: string; // e.g., "Control Room"
  tensionScore: number; // 0..1 aggregate for this room/day
  incidentCount: number; // integer
  primaryAgents: string[]; // agent names
}

export interface StageMapDayVM {
  dayIndex: number; // 0-based
  tensionTier: "low" | "medium" | "high";
  rooms: StageMapRoomVM[];
}

export interface StageMapViewModel {
  days: StageMapDayVM[];
}

/**
 * Build a minimal Stage Map VM from an EpisodeViewModel (frontend-only).
 *
 * Heuristics (Phase 4A):
 * - Rooms: If the StageEpisode exposes room structures we would use them; the current
 *   StageEpisode type has no rooms, so we fall back to a single synthetic room
 *   with id "factory_floor" and label "Factory Floor".
 * - Per-day tension per room: use day.tension_score when available. If NaN/missing → 0.
 * - Incidents per room: use day.total_incidents. If missing → 0.
 * - Primary agents: select up to 3 agent names for that day sorted by avg_stress desc,
 *   then by name asc for determinism. If missing → [].
 * - Day-level tier bands align with DayStoryboard thresholds:
 *     avg < 0.25 → "low"
 *     avg < 0.55 → "medium"
 *     else       → "high"
 * - Defensive: Always returns a valid object. On malformed input returns { days: [] }.
 */
export function buildStageMapView(
  episode: EpisodeViewModel | null | undefined
): StageMapViewModel {
  try {
    if (!episode || !episode._raw || !Array.isArray((episode as any)._raw?.days)) {
      return { days: [] };
    }

    const raw: any = (episode as any)._raw;
    const days: any[] = Array.isArray(raw.days) ? raw.days : [];

    const resultDays: StageMapDayVM[] = days
      .map((rawDay) => safeBuildDay(rawDay))
      .filter(Boolean) as StageMapDayVM[];

    // Ensure stable ordering by dayIndex
    resultDays.sort((a, b) => a.dayIndex - b.dayIndex);
    return { days: resultDays };
  } catch {
    return { days: [] };
  }
}

function safeBuildDay(rawDay: any): StageMapDayVM | null {
  if (!rawDay || typeof rawDay.day_index !== "number") return null;
  const dayIndex: number = rawDay.day_index;

  const tension = toFinite(rawDay.tension_score, 0);
  const tier = classifyTier(tension);
  const incidents = toInt(rawDay.total_incidents, 0);

  // Derive primary agents from per-day agents listing if present
  const primaryAgents = pickPrimaryAgents(rawDay);

  // Fallback single synthetic room for Phase 4A
  const rooms: StageMapRoomVM[] = [
    {
      id: "factory_floor",
      label: "Factory Floor",
      tensionScore: tension,
      incidentCount: incidents,
      primaryAgents,
    },
  ];

  // Stable ordering across rooms (if more are added in the future):
  rooms.sort((a, b) => a.label.localeCompare(b.label));

  return {
    dayIndex,
    tensionTier: tier,
    rooms,
  };
}

function pickPrimaryAgents(rawDay: any): string[] {
  try {
    const agentMap: any = rawDay?.agents;
    if (!agentMap || typeof agentMap !== "object") return [];
    const list: { name: string; stress: number }[] = Object.values(agentMap)
      .map((v: any) => ({
        name: typeof v?.name === "string" ? v.name : "",
        stress: toFinite(v?.avg_stress, 0),
      }))
      .filter((x) => x.name);
    list.sort((a, b) => {
      if (b.stress !== a.stress) return b.stress - a.stress;
      return a.name.localeCompare(b.name);
    });
    return list.slice(0, 3).map((x) => x.name);
  } catch {
    return [];
  }
}

function classifyTier(v: number): "low" | "medium" | "high" {
  if (!isFinite(v) || v < 0) v = 0;
  if (v < 0.25) return "low";
  if (v < 0.55) return "medium";
  return "high";
}

function toFinite(n: unknown, fallback: number): number {
  const v = typeof n === "number" ? n : Number.NaN;
  return Number.isFinite(v) ? v : fallback;
}

function toInt(n: unknown, fallback: number): number {
  const v = typeof n === "number" ? Math.trunc(n) : Number.NaN;
  return Number.isFinite(v) ? v : fallback;
}

export type { StageMapViewModel as TStageMapViewModel };
