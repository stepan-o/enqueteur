// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import TimelineStrip from "./TimelineStrip";
import type { DayViewModel } from "../vm/dayVm";

describe("TimelineStrip", () => {
  const days: DayViewModel[] = [
    { index: 0, tensionScore: 0.1, totalIncidents: 1, perceptionMode: "normal", supervisorActivity: 0.0 },
    { index: 1, tensionScore: 0.5, totalIncidents: 2, perceptionMode: "alert", supervisorActivity: 0.2 },
  ];
  const tensionTrend = [0.1, 0.5];

  it("renders one button per day", () => {
    render(
      <TimelineStrip days={days} tensionTrend={tensionTrend} selectedIndex={null} />
    );

    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(2);
    expect(screen.getByText(/Day 0/)).toBeTruthy();
    expect(screen.getByText(/Day 1/)).toBeTruthy();
  });

  it("marks the selected day with 'selected' class", () => {
    const { container } = render(
      <TimelineStrip days={days} tensionTrend={tensionTrend} selectedIndex={1} />
    );

    const selected = within(container).getByTestId("timeline-day-1");
    expect(selected.getAttribute("aria-selected")).toBe("true");
  });

  it("calls onSelect with the day index when clicked", () => {
    const handleSelect = vi.fn();
    const { container } = render(
      <TimelineStrip
        days={days}
        tensionTrend={tensionTrend}
        selectedIndex={null}
        onSelect={handleSelect}
      />
    );

    const buttons = within(container).getAllByRole("button");
    fireEvent.click(buttons[0]);
    expect(handleSelect).toHaveBeenCalledWith(0);
  });

  it("renders an empty state when no days", () => {
    render(
      <TimelineStrip days={[]} tensionTrend={[]} selectedIndex={null} />
    );
    expect(screen.getByText(/No days in this episode/i)).toBeTruthy();
  });
});
