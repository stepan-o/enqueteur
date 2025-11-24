import type { StageEpisode } from "../types/stage";
import type { AgentViewModel } from "./agentVm";
import type { DayViewModel } from "./dayVm";
import { buildAgentViews } from "./agentVm";
import { buildDayViews } from "./dayVm";

export interface EpisodeViewModel {
  id: string | null;
  runId: string | null;
  index: number;
  stageVersion: number;
  days: DayViewModel[];
  agents: AgentViewModel[];
  tensionTrend: number[];
}

export function buildEpisodeView(ep: StageEpisode): EpisodeViewModel {
  return {
    id: ep.episode_id ?? null,
    runId: ep.run_id ?? null,
    index: ep.episode_index,
    stageVersion: ep.stage_version,
    days: buildDayViews(ep.days),
    agents: buildAgentViews(ep),
    tensionTrend: ep.tension_trend,
  };
}
