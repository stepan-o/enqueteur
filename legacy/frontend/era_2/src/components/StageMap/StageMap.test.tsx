// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, within } from "@testing-library/react";
import StageMap from ".";
import type { StageMapViewModel } from "../../vm/stageMapVm";

function makeVM(): StageMapViewModel {
  return {
    days: [
      {
        dayIndex: 0,
        tensionTier: "medium",
        rooms: [
          {
            id: "factory_floor",
            label: "Factory Floor",
            tensionScore: 0.35,
            incidentCount: 1,
            primaryAgents: ["Ava", "Bob"],
          },
          {
            id: "control_room",
            label: "Control Room",
            tensionScore: 0.2,
            incidentCount: 0,
            primaryAgents: ["Cara"],
          },
        ],
      },
      {
        dayIndex: 1,
        tensionTier: "high",
        rooms: [
          {
            id: "factory_floor",
            label: "Factory Floor",
            tensionScore: 0.8,
            incidentCount: 3,
            primaryAgents: ["Ava"],
          },
        ],
      },
    ],
  };
}

describe("<StageMap />", () => {
  it("renders all rooms for selected day and applies tension tier hook", () => {
    const vm = makeVM();
    const { container } = render(
      <StageMap viewModel={vm} selectedDayIndex={0} />
    );
    const root = within(container).getByRole("group", { name: /stage map/i });
    const tiles = within(root).getAllByRole("img");
    // Two rooms on day 0
    expect(tiles.length).toBe(2);
    // Ensure data attribute for tier present on tiles
    tiles.forEach((el) => {
      expect(el.getAttribute("data-tension-tier")).toBe("medium");
    });
    // Accessible labels contain room name and agent summary
    const labels = tiles.map((el) => el.getAttribute("aria-label") || "");
    expect(labels.some((t) => /Factory Floor, medium tension/i.test(t))).toBe(true);
    expect(labels.some((t) => /Control Room, medium tension/i.test(t))).toBe(true);
    expect(labels.some((t) => /2 agents active/i.test(t))).toBe(true);
  });

  it("renders neutral map when selectedDayIndex is null", () => {
    const vm = makeVM();
    const { container, getByText } = render(
      <StageMap viewModel={vm} selectedDayIndex={null} />
    );
    expect(getByText(/No day selected/i)).toBeTruthy();
    const root = within(container).getByRole("group", { name: /stage map/i });
    const imgs = within(root).getAllByRole("img");
    // Neutral tiles have low tension
    imgs.forEach((el) => {
      expect(el.getAttribute("data-tension-tier")).toBe("low");
    });
  });

  it("renders neutral map when selectedDayIndex is out of range", () => {
    const vm = makeVM();
    const { container } = render(
      <StageMap viewModel={vm} selectedDayIndex={99} />
    );
    const captions = within(container).getAllByText(/No day selected/i);
    expect(captions.length).toBeGreaterThan(0);
    // Ensure we are looking at the current render only
    const root = within(container).getByRole("group", { name: /stage map/i });
    expect(within(root).getAllByRole("img").length).toBeGreaterThan(0);
  });

  it("supports high/low tiers on different days", () => {
    const vm = makeVM();
    const { rerender, container } = render(
      <StageMap viewModel={vm} selectedDayIndex={1} />
    );
    let tiles = within(container).getAllByRole("img");
    expect(tiles[0].getAttribute("data-tension-tier")).toBe("high");
    rerender(<StageMap viewModel={vm} selectedDayIndex={0} />);
    tiles = within(container).getAllByRole("img");
    expect(tiles[0].getAttribute("data-tension-tier")).toBe("medium");
  });
});
