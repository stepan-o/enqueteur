import type { EpisodeViewModel } from "./episodeVm";
import type { StageNarrativeBlock, StageEpisode, StageDay } from "../types/stage";

export interface DayAgentDetail {
  name: string;
  role: string;
  avgStress: number;
  guardrailCount: number;
  contextCount: number;
  emotionalRead: Record<string, unknown> | null;
  attributionCause: string | null;
}

export interface DayDetailViewModel {
  index: number;
  perceptionMode: string;
  tensionScore: number;
  totalIncidents: number;
  supervisorActivity: number;

  narrative: StageNarrativeBlock[];
  agents: DayAgentDetail[];
}

function findStageDay(raw: StageEpisode | undefined, dayIndex: number): StageDay | undefined {
  if (!raw) return undefined;
  return raw.days.find((d) => d.day_index === dayIndex);
}

export function buildDayDetail(ep: EpisodeViewModel, dayIndex: number): DayDetailViewModel {
  const day = findStageDay((ep as any)._raw as StageEpisode | undefined, dayIndex);

  if (!day) {
    return {
      index: dayIndex,
      perceptionMode: "unknown",
      tensionScore: 0,
      totalIncidents: 0,
      supervisorActivity: 0,
      narrative: [],
      agents: [],
    };
  }

  const agents: DayAgentDetail[] = Object.values(day.agents ?? {}).map((a) => ({
    name: a.name,
    role: a.role,
    avgStress: (a as any).avg_stress ?? 0,
    guardrailCount: (a as any).guardrail_count ?? 0,
    contextCount: (a as any).context_count ?? 0,
    emotionalRead:
      a.emotional_read && typeof a.emotional_read === "object"
        ? (a.emotional_read as Record<string, unknown>)
        : null,
    attributionCause: typeof a.attribution_cause === "string" ? a.attribution_cause : null,
  }));

  agents.sort((a, b) => a.name.localeCompare(b.name));

  return {
    index: day.day_index,
    perceptionMode: day.perception_mode,
    tensionScore: day.tension_score ?? 0,
    totalIncidents: day.total_incidents ?? 0,
    supervisorActivity: day.supervisor_activity ?? 0,
    narrative: day.narrative ?? [],
    agents,
  };
}
