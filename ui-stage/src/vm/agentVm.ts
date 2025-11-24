import type { StageEpisode } from "../types/stage";

export interface AgentViewModel {
  name: string;
  role: string;
  stressStart: number;
  stressEnd: number;
  stressDelta: number;
  guardrailTotal: number;
  contextTotal: number;
  visual: string;
  vibe: string;
  tagline: string;
}

export function buildAgentViews(ep: StageEpisode): AgentViewModel[] {
  const list: AgentViewModel[] = Object.entries(ep.agents).map(([name, a]) => {
    const start = a.stress_start ?? 0;
    const end = a.stress_end ?? 0;
    return {
      name: a.name || name,
      role: a.role,
      stressStart: start,
      stressEnd: end,
      stressDelta: end - start,
      guardrailTotal: a.guardrail_total,
      contextTotal: a.context_total,
      visual: a.visual,
      vibe: a.vibe,
      tagline: a.tagline,
    };
  });

  // Stable ordering for UI rendering
  list.sort((a, b) => a.name.localeCompare(b.name));
  return list;
}
