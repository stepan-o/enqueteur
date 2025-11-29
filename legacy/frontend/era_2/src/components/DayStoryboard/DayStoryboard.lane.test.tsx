// @vitest-environment jsdom
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, it, expect, afterEach, vi } from "vitest";
import DayStoryboardList from "./DayStoryboardList";

const items = [
  {
    dayIndex: 0,
    label: "Day 0",
    caption: "Alpha",
    tensionScore: 0.1,
    hasIncidents: false,
    supervisorActivity: 0,
    narrativeLane: [
      { lane: "narrative" as const, dayIndex: 0, blockId: "n0", kind: "beat", text: "A0", tags: [] },
      { lane: "narrative" as const, dayIndex: 0, blockId: "n1", kind: "aside", text: "A1", tags: [] },
    ],
  },
  {
    dayIndex: 1,
    label: "Day 1",
    caption: "Bravo",
    tensionScore: 0.2,
    hasIncidents: true,
    supervisorActivity: 0.5,
    narrativeLane: [
      { lane: "narrative" as const, dayIndex: 1, blockId: "m0", kind: "beat", text: "B0", tags: [] },
    ],
  },
];

describe("DayStoryboard Narrative Lane", () => {
  afterEach(() => cleanup());

  it("renders narrative lane items with accessibility and selection attributes", () => {
    render(
      <DayStoryboardList
        items={items as any}
        selectedDayIndex={0}
        onSelectDay={vi.fn()}
        selectedNarrativeBlockId={"n1"}
      />
    );
    const lane = screen.getByLabelText(/Day 0 narrative items/i);
    expect(lane).toBeTruthy();
    const buttons = lane.querySelectorAll("[data-lane='narrative']");
    expect(buttons.length).toBe(2);
    const selected = Array.from(buttons).find((b) => b.getAttribute("data-selected") === "true");
    expect(selected).toBeTruthy();
    expect(selected?.getAttribute("data-block-id")).toBe("n1");
  });

  it("invokes onSelectNarrativeItem and updates selection deterministically", () => {
    const onSelectNarrativeItem = vi.fn();
    render(
      <DayStoryboardList
        items={items as any}
        selectedDayIndex={0}
        onSelectDay={vi.fn()}
        onSelectNarrativeItem={onSelectNarrativeItem}
      />
    );
    const lane = screen.getByLabelText(/Day 0 narrative items/i);
    const btn = lane.querySelector("[data-block-id='n0']") as HTMLButtonElement;
    fireEvent.click(btn);
    expect(onSelectNarrativeItem).toHaveBeenCalled();
    const arg = onSelectNarrativeItem.mock.calls[0][0];
    expect(arg.blockId).toBe("n0");
    expect(arg.lane).toBe("narrative");
  });
});
