import { describe, it, expectTypeOf } from "vitest";
import type {
  StageEpisode,
  StageDay,
  StageNarrativeBlock,
  StageAgentDayView,
  StageAgentSummary,
  StageAgentTraits,
} from "./types/stage";

describe("Stage types contract", () => {
  it("StageNarrativeBlock shape", () => {
    const block: StageNarrativeBlock = {
      block_id: "b1",
      kind: "recap",
      text: "Day opened with a tense briefing.",
      day_index: 0,
      agent_name: "Ava",
      tags: ["briefing", "tension"],
    };
    expectTypeOf(block.kind).toBeString();
  });

  it("StageAgentTraits optional snapshot", () => {
    const traits: StageAgentTraits = {
      resilience: 0.7,
      agency: 0.5,
    };
    expectTypeOf(traits.resilience).toBeNumber();
  });

  it("StageEpisode end-to-end shape", () => {
    const episode: StageEpisode = {
      episode_id: "ep-123",
      run_id: "run-456",
      episode_index: 2,
      stage_version: 1,
      tension_trend: [0.2, 0.4, 0.35],

      days: [
        {
          day_index: 0,
          perception_mode: "normal",
          tension_score: 0.2,
          agents: {
            Ava: {
              name: "Ava",
              role: "analyst",
              avg_stress: 0.3,
              guardrail_count: 1,
              context_count: 2,
              emotional_read: { mood: "calm", certainty: 0.8, energy: 0.6 },
              attribution_cause: "system",
              narrative: [
                {
                  block_id: "b1",
                  kind: "beat",
                  text: "Ava reviewed the logs.",
                  day_index: 0,
                  agent_name: "Ava",
                  tags: ["review"],
                },
              ],
            },
          },
          total_incidents: 1,
          supervisor_activity: 0.1,
          narrative: [
            {
              block_id: "n1",
              kind: "recap",
              text: "The team aligned on goals.",
              day_index: 0,
              agent_name: null,
              tags: ["recap"],
            },
          ],
        },
      ],

      agents: {
        Ava: {
          name: "Ava",
          role: "analyst",
          guardrail_total: 2,
          context_total: 3,
          stress_start: 0.25,
          stress_end: 0.35,
          trait_snapshot: {
            resilience: 0.7,
            caution: 0.4,
          },
          visual: "avatar_ava",
          vibe: "focused",
          tagline: "Logs never lie.",
        },
      },

      story_arc: { theme: "containment", beats: ["rising tension", "setback"] },
      narrative: [
        {
          block_id: "g1",
          kind: "aside",
          text: "A quiet moment before the storm.",
          day_index: 0,
          agent_name: null,
          tags: ["tone"],
        },
      ],
      long_memory: {
        Ava: { key_events: ["promotion"], sentiment: "loyal" },
      },
      character_defs: {
        Ava: { role: "analyst", color: "#44a" },
      },
    } satisfies StageEpisode;

    expectTypeOf(episode.days[0].agents.Ava.narrative[0].tags).toMatchTypeOf<string[]>();
  });
});
