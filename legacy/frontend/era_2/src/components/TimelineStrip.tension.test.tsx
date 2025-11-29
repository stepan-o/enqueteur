// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, within } from "@testing-library/react";
import TimelineStrip from "./TimelineStrip";
import type { DayViewModel } from "../vm/dayVm";
import { tensionColor } from "../utils/tensionColors";

function cssColor(val: string): string {
  const el = document.createElement("div");
  el.style.backgroundColor = val;
  return el.style.backgroundColor;
}

describe("TimelineStrip tension visuals", () => {
  const days: DayViewModel[] = [
    { index: 0, tensionScore: 0.12, totalIncidents: 0, perceptionMode: "normal", supervisorActivity: 0 },
    { index: 1, tensionScore: 0.44, totalIncidents: 1, perceptionMode: "alert", supervisorActivity: 0.1 },
    { index: 2, tensionScore: 0.8, totalIncidents: 2, perceptionMode: "alert", supervisorActivity: 0.2 },
  ];

  it("renders a dot per day with correct background color", () => {
    const { container } = render(
      <TimelineStrip days={days} selectedIndex={1} onSelect={vi.fn()} />
    );

    days.forEach((d) => {
      const dot = within(container).getByTestId(`timeline-dot-${d.index}`) as HTMLElement;
      const actual = (dot.style as CSSStyleDeclaration).backgroundColor;
      const expected = cssColor(tensionColor(d.tensionScore));
      expect(actual).toBe(expected);
    });
  });

  it("shows selection ring on selected day dot only", () => {
    const { container, rerender } = render(
      <TimelineStrip days={days} selectedIndex={1} onSelect={vi.fn()} />
    );

    const selectedDot = within(container).getByTestId("timeline-dot-1");
    expect(selectedDot.getAttribute("data-selected")).toBe("true");

    const nonSelectedDot = within(container).getByTestId("timeline-dot-0");
    expect(nonSelectedDot.getAttribute("data-selected")).toBe("false");

    // move selection to 2 and validate
    rerender(<TimelineStrip days={days} selectedIndex={2} onSelect={vi.fn()} />);
    const sel2 = within(container).getByTestId("timeline-dot-2");
    expect(sel2.getAttribute("data-selected")).toBe("true");
  });

  it("dot count matches days length and titles include tension", () => {
    const { container } = render(
      <TimelineStrip days={days} selectedIndex={0} onSelect={vi.fn()} />
    );
    const buttons = within(container).getAllByRole("button");
    expect(buttons.length).toBe(days.length);

    // title attribute lives on the button; updated format "Day X • Tension 0.xx"
    const btn1 = within(container).getByTestId("timeline-day-1");
    expect(btn1.getAttribute("title") || "").toMatch(/Day 1 \u2022 Tension 0\.44/);
  });
});
