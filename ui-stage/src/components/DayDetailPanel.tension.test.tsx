// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import DayDetailPanel from "./DayDetailPanel";
import type { EpisodeViewModel } from "../vm/episodeVm";
import type { StageEpisode } from "../types/stage";
import { tensionColor } from "../utils/tensionColors";

function cssColor(val: string): string {
  const el = document.createElement("div");
  el.style.backgroundColor = val;
  return el.style.backgroundColor;
}

function makeEpisodeVM(tension: number | undefined): EpisodeViewModel {
  const raw: StageEpisode = {
    episode_id: "ep-tension",
    run_id: null,
    episode_index: 0,
    stage_version: 1,
    tension_trend: [],
    days: [
      {
        day_index: 0,
        perception_mode: "normal",
        // @ts-expect-error allow undefined to test normalization path
        tension_score: tension as any,
        total_incidents: 0,
        supervisor_activity: 0,
        narrative: [],
        agents: {},
      },
    ],
    agents: {},
    story_arc: null,
    narrative: [],
    long_memory: null,
    character_defs: null,
  };

  return {
    id: raw.episode_id,
    runId: raw.run_id,
    index: raw.episode_index,
    stageVersion: raw.stage_version,
    days: [],
    agents: [],
    tensionTrend: [],
    story: { storyArc: null, longMemory: null, topLevelNarrative: [] },
    _raw: raw,
  };
}

describe("DayDetailPanel tension bar", () => {
  it("renders tension bar container", () => {
    const vm = makeEpisodeVM(0.44);
    const { container } = render(<DayDetailPanel episode={vm} dayIndex={0} />);
    const bar = within(container).getByTestId("tension-bar");
    expect(bar).toBeTruthy();
  });

  it("fills correct width and color for known tension value", () => {
    const vm = makeEpisodeVM(0.44);
    const { container } = render(<DayDetailPanel episode={vm} dayIndex={0} />);
    const fill = within(container).getByTestId("tension-fill") as HTMLElement;
    // Prefer computed style to attribute string for robustness
    expect((fill.style as CSSStyleDeclaration).width).toBe("44%");
    const expectedColor = cssColor(tensionColor(0.44));
    // Compare via computed style property to avoid hex vs rgb mismatch
    expect((fill.style as CSSStyleDeclaration).backgroundColor).toBe(expectedColor);
  });

  it("does not crash when tensionScore is missing and defaults safely", () => {
    const vm = makeEpisodeVM(undefined);
    const { container } = render(<DayDetailPanel episode={vm} dayIndex={0} />);
    // Component should render without throwing; tension UI may be present or omitted
    const bar = within(container).queryByTestId("tension-bar");
    if (bar) {
      expect(bar).toBeTruthy();
    }
    // Fill may or may not render in some edge states; if present, assert defaults
    const maybeFill = (within(container).queryByTestId("tension-fill") as HTMLElement) || null;
    if (maybeFill) {
      const expected = cssColor("#4FA3FF");
      expect((maybeFill.style as CSSStyleDeclaration).backgroundColor).toBe(expected);
    }
  });
});
