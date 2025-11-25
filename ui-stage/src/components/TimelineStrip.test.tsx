// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, fireEvent, within } from "@testing-library/react";
import TimelineStrip from "./TimelineStrip";
import type { DayViewModel } from "../vm/dayVm";
import type { DaySummaryViewModel } from "../vm/daySummaryVm";

describe("TimelineStrip", () => {
  const days: DayViewModel[] = [
    { index: 0, tensionScore: 0.1, totalIncidents: 1, perceptionMode: "normal", supervisorActivity: 0 },
    { index: 1, tensionScore: 0.5, totalIncidents: 2, perceptionMode: "alert", supervisorActivity: 0.2 },
  ];

  it("renders all days", () => {
    const { getByText, getAllByRole } = render(
      <TimelineStrip days={days} selectedIndex={0} onSelect={vi.fn()} />
    );

    const buttons = getAllByRole("button");
    expect(buttons).toHaveLength(2);
    expect(getByText(/Day 0/)).toBeTruthy();
    expect(getByText(/Day 1/)).toBeTruthy();
  });

  it("highlights selected day", () => {
    const { container } = render(
      <TimelineStrip days={days} selectedIndex={1} onSelect={vi.fn()} />
    );

    const selected = within(container).getByTestId("timeline-day-1");
    expect(selected.getAttribute("aria-selected")).toBe("true");

    const nonSelected = within(container).getByTestId("timeline-day-0");
    expect(nonSelected.getAttribute("aria-selected")).toBe("false");
  });

  it("calls onSelect on click", () => {
    const handleSelect = vi.fn();
    const { container } = render(
      <TimelineStrip days={days} selectedIndex={0} onSelect={handleSelect} />
    );

    fireEvent.click(within(container).getByText(/Day 1/));
    expect(handleSelect).toHaveBeenCalledTimes(1);
    expect(handleSelect).toHaveBeenCalledWith(1);
  });

  it("applies selection ring class on selected dot", () => {
    const { container } = render(
      <TimelineStrip days={days} selectedIndex={1} onSelect={vi.fn()} />
    );

    const selectedDot = within(container).getByTestId("timeline-dot-1");
    const nonSelectedDot = within(container).getByTestId("timeline-dot-0");

    // data-selected remains the canonical indicator
    expect(selectedDot.getAttribute("data-selected")).toBe("true");
    expect(nonSelectedDot.getAttribute("data-selected")).toBe("false");

    // and class should include the selection ring class from CSS modules
    expect((selectedDot as HTMLElement).className).toMatch(/dotSelected/);
    expect((nonSelectedDot as HTMLElement).className).not.toMatch(/dotSelected/);
  });

  it("sets data-focus on keyboard focus for accessibility ring", () => {
    const { container } = render(
      <TimelineStrip days={days} selectedIndex={0} onSelect={vi.fn()} />
    );
    const button = within(container).getByTestId("timeline-day-0");

    // focus event should set data-focus
    button.focus();
    expect(button.getAttribute("data-focus")).toBe("true");

    // blur clears it
    (button as HTMLElement).blur();
    expect(button.getAttribute("data-focus")).toBeNull();
  });

  it("marks strip as horizontally scrollable via data attribute", () => {
    const { container } = render(
      <TimelineStrip days={days} selectedIndex={0} onSelect={vi.fn()} />
    );
    const strip = container.firstElementChild as HTMLElement;
    expect(strip.getAttribute("data-scroll")).toBe("x");
  });

  it("does not crash on empty days", () => {
    const { container } = render(
      <TimelineStrip days={[]} selectedIndex={0} onSelect={vi.fn()} />
    );
    // Renders an empty strip (no buttons)
    const btns = within(container).queryAllByRole("button");
    expect(btns.length).toBe(0);
  });

  it("renders summary indicators when provided (arrow + agent)", () => {
    const summaries: DaySummaryViewModel[] = [
      {
        dayIndex: 0,
        tensionDirection: "up",
        tensionChange: 0.2,
        primaryAgentName: "Ava",
        primaryAgentStress: 0.63,
        notableText: "Tension rose compared...",
      },
      {
        dayIndex: 1,
        tensionDirection: "flat",
        tensionChange: 0.0,
        primaryAgentName: null,
        primaryAgentStress: null,
        notableText: "Tension held steady...",
      },
    ];

    const { container } = render(
      <TimelineStrip
        days={days}
        selectedIndex={0}
        onSelect={vi.fn()}
        daySummaries={summaries}
      />
    );

    const day0 = within(container).getByTestId("timeline-day-0");
    const day1 = within(container).getByTestId("timeline-day-1");

    expect(day0.textContent || "").toMatch(/▲/);
    expect(day0.textContent || "").toMatch(/Ava/);

    expect(day1.textContent || "").toMatch(/▬/);
  });

  it("handles missing summaries array or mismatched entries without crashing", () => {
    // No summaries prop at all
    const r1 = render(
      <TimelineStrip days={days} selectedIndex={0} onSelect={vi.fn()} />
    );
    const day0a = within(r1.container).getByTestId("timeline-day-0");
    expect(day0a.textContent || "").not.toMatch(/[▲▼▬]/);
    r1.unmount();

    // Summaries shorter than days
    const shortSummaries: DaySummaryViewModel[] = [
      {
        dayIndex: 0,
        tensionDirection: "down",
        tensionChange: -0.3,
        primaryAgentName: null,
        primaryAgentStress: null,
        notableText: "Tension fell...",
      },
    ];
    const { container } = render(
      <TimelineStrip
        days={days}
        selectedIndex={1}
        onSelect={vi.fn()}
        daySummaries={shortSummaries}
      />
    );
    const day0 = within(container).getByTestId("timeline-day-0");
    const day1 = within(container).getByTestId("timeline-day-1");
    expect(day0.textContent || "").toMatch(/▼/);
    expect(day1.textContent || "").not.toMatch(/[▲▼▬]/);
  });
});
