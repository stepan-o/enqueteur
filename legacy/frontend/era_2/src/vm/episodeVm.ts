import type { StageEpisode } from "../types/stage";
import type { AgentViewModel } from "./agentVm";
import type { DayViewModel } from "./dayVm";
import { buildAgentViews } from "./agentVm";
import { buildDayViews } from "./dayVm";
import type { EpisodeStoryViewModel } from "./storyVm";
import { buildStoryView } from "./storyVm";
import type { DaySummaryViewModel } from "./daySummaryVm";
import { buildDaySummary } from "./daySummaryVm";

export interface EpisodeViewModel {
  id: string | null;
  runId: string | null;
  index: number;
  stageVersion: number;
  days: DayViewModel[];
  agents: AgentViewModel[];
  tensionTrend: number[];
  story: EpisodeStoryViewModel;
  /** Optional, additive summaries of each day for TimelineStrip “spine” rendering. */
  daySummaries?: DaySummaryViewModel[];
  /**
   * Raw StageEpisode backing this VM. Internal use only for detail builders;
   * UI should not rely on this shape.
   */
  _raw: StageEpisode;
}

export function buildEpisodeView(ep: StageEpisode): EpisodeViewModel {
  // Build base VM first
  const base: EpisodeViewModel = {
    id: ep.episode_id ?? null,
    runId: ep.run_id ?? null,
    index: ep.episode_index,
    stageVersion: ep.stage_version,
    days: buildDayViews(ep.days),
    agents: buildAgentViews(ep),
    tensionTrend: ep.tension_trend,
    story: buildStoryView(ep),
    _raw: ep,
  };

  // Compute additive day summaries using existing builders; keep ordering by dayIndex
  try {
    const dayIndices = Array.isArray(ep.days)
      ? ep.days.map((d) => d.day_index).filter((n) => typeof n === "number")
      : [];
    const summaries: DaySummaryViewModel[] = dayIndices.map((idx) =>
      buildDaySummary(base, idx)
    );
    return { ...base, daySummaries: summaries };
  } catch {
    // Fail-soft: if anything goes wrong, return base unchanged
    return base;
  }
}
