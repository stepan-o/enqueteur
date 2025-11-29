// @vitest-environment jsdom
import { render, screen, cleanup } from "@testing-library/react";
import { describe, it, expect, afterEach } from "vitest";
import DayStoryboardStrip from "./DayStoryboardStrip";

describe("DayStoryboardStrip — tension band and sparkline", () => {
  // Ensure DOM is reset between tests to avoid duplicate elements
  afterEach(() => cleanup());

  function makeItem(overrides: Partial<any> = {}) {
    return {
      dayIndex: 1,
      label: "Day 1",
      caption: "Test caption",
      tensionScore: 0.6,
      hasIncidents: false,
      supervisorActivity: 0,
      narrativeLane: [],
      sparklinePoints: [0, 1],
      tensionBandClass: "tensionHigh",
      ...overrides,
    } as any;
  }

  it("applies band class via data-band and renders sparkline SVG with label", () => {
    const item = makeItem();
    render(
      <DayStoryboardStrip
        item={item}
        isSelected={false}
        onSelect={() => {}}
      />
    );

    const root = screen.getByTestId("day-storyboard-strip-1");
    expect(root.getAttribute("data-band")).toBe("tensionHigh");

    const sparkWrap = screen.getByLabelText(/Tension trend for Day 1/i);
    // aria-label should summarize trend
    expect(sparkWrap.getAttribute("aria-label") || "").toMatch(/Tension trend for Day 1/i);
    // SVG present
    const svg = sparkWrap.querySelector("svg");
    expect(svg).toBeTruthy();
    // a path is drawn
    const path = sparkWrap.querySelector("path");
    expect(path).toBeTruthy();
  });

  it("does not render sparkline when sparklinePoints empty", () => {
    const item = makeItem({ sparklinePoints: [] });
    render(
      <DayStoryboardStrip item={item} isSelected={false} onSelect={() => {}} />
    );
    // Target the steady trend label to avoid ambiguity if multiple elements exist
    const sparkWrap = screen.getByLabelText(/Tension trend for Day 1: steady/i);
    expect(sparkWrap).toBeTruthy();
    expect(sparkWrap.querySelector("svg")).toBeNull();
  });
});
