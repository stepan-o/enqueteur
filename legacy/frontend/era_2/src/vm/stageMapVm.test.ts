// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import type { EpisodeViewModel } from "./episodeVm";
import type { StageEpisode } from "../types/stage";
import { buildStageMapView, type StageMapViewModel } from "./stageMapVm";

function makeEpisode(rawOverrides?: Partial<StageEpisode>): EpisodeViewModel {
  const raw: StageEpisode = {
    episode_id: "ep-1",
    run_id: "run-1",
    episode_index: 0,
    stage_version: 1,
    tension_trend: [],
    days: [],
    agents: {},
    story_arc: null,
    narrative: [],
    long_memory: null,
    character_defs: null,
    ...rawOverrides,
  } as StageEpisode;

  return {
    id: raw.episode_id,
    runId: raw.run_id,
    index: raw.episode_index,
    stageVersion: raw.stage_version,
    days: [],
    agents: [],
    tensionTrend: raw.tension_trend ?? [],
    story: { storyArc: null, longMemory: null, topLevelNarrative: [] },
    _raw: raw,
  } as unknown as EpisodeViewModel;
}

describe("stageMapVm", () => {
  it("returns empty days when episode is null or malformed", () => {
    expect(buildStageMapView(null).days.length).toBe(0);
    expect(buildStageMapView({} as any).days.length).toBe(0);
  });

  it("handles episode with 0 days", () => {
    const vm = makeEpisode({ days: [] });
    const map = buildStageMapView(vm);
    expect(map.days).toEqual([]);
  });

  it("builds a single synthetic room per day with derived metrics", () => {
    const vm = makeEpisode({
      days: [
        {
          day_index: 0,
          perception_mode: "normal",
          tension_score: 0.6,
          total_incidents: 2,
          supervisor_activity: 0,
          narrative: [],
          agents: {
            Ava: {
              name: "Ava",
              role: "ops",
              avg_stress: 0.8,
              guardrail_count: 0,
              context_count: 0,
              emotional_read: null,
              attribution_cause: null,
              narrative: [],
            },
            Bob: {
              name: "Bob",
              role: "tech",
              avg_stress: 0.3,
              guardrail_count: 0,
              context_count: 0,
              emotional_read: null,
              attribution_cause: null,
              narrative: [],
            },
          },
        },
      ],
    });
    const map = buildStageMapView(vm);
    expect(map.days.length).toBe(1);
    const d0 = map.days[0];
    expect(d0.dayIndex).toBe(0);
    expect(d0.tensionTier).toBe("high"); // 0.6 → high tier
    expect(d0.rooms.length).toBe(1);
    const r = d0.rooms[0];
    expect(r.id).toBe("factory_floor");
    expect(r.tensionScore).toBe(0.6);
    expect(r.incidentCount).toBe(2);
    // Primary agents sorted by stress desc, then name
    expect(r.primaryAgents).toEqual(["Ava", "Bob"]);
  });

  it("computes medium/low tiers per thresholds and is deterministic across days", () => {
    const vm = makeEpisode({
      days: [
        {
          day_index: 1,
          perception_mode: "normal",
          tension_score: 0.24,
          total_incidents: 0,
          supervisor_activity: 0,
          narrative: [],
          agents: {},
        },
        {
          day_index: 0,
          perception_mode: "normal",
          tension_score: 0.35,
          total_incidents: 1,
          supervisor_activity: 0,
          narrative: [],
          agents: {},
        },
      ],
    });
    const map = buildStageMapView(vm);
    // Sorted by dayIndex
    expect(map.days.map((d) => d.dayIndex)).toEqual([0, 1]);
    expect(map.days[0].tensionTier).toBe("medium"); // 0.35 → medium
    expect(map.days[1].tensionTier).toBe("low"); // 0.24 → low
  });

  it("falls back safely when agents data is junk and incidents/tension missing", () => {
    const vm = makeEpisode({
      days: [
        {
          day_index: 0,
          perception_mode: "normal",
          tension_score: undefined as unknown as number,
          total_incidents: undefined as unknown as number,
          supervisor_activity: 0,
          narrative: [],
          agents: null as unknown as any,
        },
      ],
    });
    const map: StageMapViewModel = buildStageMapView(vm);
    const d0 = map.days[0];
    expect(d0.tensionTier).toBe("low");
    expect(d0.rooms[0].tensionScore).toBe(0);
    expect(d0.rooms[0].incidentCount).toBe(0);
    expect(d0.rooms[0].primaryAgents).toEqual([]);
  });
});
