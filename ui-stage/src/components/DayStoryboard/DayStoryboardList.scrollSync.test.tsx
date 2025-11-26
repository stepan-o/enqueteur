// @vitest-environment jsdom
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, it, expect, afterEach, vi } from "vitest";
import DayStoryboardList from "./DayStoryboardList";

function makeItems(n = 3) {
  return Array.from({ length: n }).map((_, i) => ({
    dayIndex: i,
    label: `Day ${i}`,
    caption: `Caption ${i}`,
    tensionScore: 0.1 * i,
    hasIncidents: i % 2 === 0,
    supervisorActivity: 0,
    narrativeLane: [],
  }));
}

describe("DayStoryboardList — scroll sync", () => {
  afterEach(() => cleanup());

  it("calls onSelectDay with dominant strip on scroll (center heuristic)", async () => {
    const items = makeItems(3);
    const onSelectDay = vi.fn();
    render(
      <DayStoryboardList
        items={items as any}
        selectedDayIndex={0}
        onSelectDay={onSelectDay}
      />
    );

    const container = await screen.findByTestId("day-storyboard-container");

    // Ensure rAF runs immediately in jsdom tests
    const rafSpy = vi
      .spyOn(globalThis, "requestAnimationFrame")
      // @ts-expect-error timings
      .mockImplementation((cb: FrameRequestCallback) => {
        cb(0 as any);
        return 1 as any;
      });

    // Stub container rect to fixed area
    const containerRect = { top: 100, height: 300, left: 0, width: 600, bottom: 400, right: 600 } as DOMRect as any;
    vi.spyOn(container, "getBoundingClientRect").mockReturnValue(containerRect);

    // Find strip wrappers and stub their rects so that index 2 is closest to center
    const wrappers = Array.from(container.querySelectorAll("[data-day-index]")) as HTMLElement[];
    // index 0 at top, 1 mid, 2 closest to center
    const rects: Record<number, any> = {
      0: { top: 110, height: 60, left: 0, width: 500, bottom: 170, right: 500 }, // center 140 (dist 110)
      1: { top: 210, height: 60, left: 0, width: 500, bottom: 270, right: 500 }, // center 240 (dist 10)
      2: { top: 220, height: 60, left: 0, width: 500, bottom: 280, right: 500 }, // center 250 (dist 0) → dominant
    };
    for (const w of wrappers) {
      const idx = Number(w.getAttribute("data-day-index"));
      vi.spyOn(w, "getBoundingClientRect").mockReturnValue(rects[idx]);
    }

    // Fire scroll event; rAF defers selection, so flush it
    fireEvent.scroll(container);

    expect(onSelectDay).toHaveBeenCalled();
    const call = onSelectDay.mock.calls[onSelectDay.mock.calls.length - 1][0];
    expect(call).toBe(2);
    rafSpy.mockRestore();
  });

  it("scrolls selected strip into view when selectedDayIndex changes", async () => {
    const items = makeItems(2) as any;
    const onSelectDay = vi.fn();
    const { rerender } = render(
      <DayStoryboardList items={items} selectedDayIndex={0} onSelectDay={onSelectDay} />
    );
    const container = await screen.findByTestId("day-storyboard-container");
    const target = container.querySelector('[data-day-index="1"]') as any;
    target.scrollIntoView = vi.fn();

    // Change selection
    rerender(
      <DayStoryboardList items={items} selectedDayIndex={1} onSelectDay={onSelectDay} />
    );

    expect(target.scrollIntoView).toHaveBeenCalled();
  });
});
