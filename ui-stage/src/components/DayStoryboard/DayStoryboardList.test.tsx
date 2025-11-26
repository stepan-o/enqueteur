// @vitest-environment jsdom
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import DayStoryboardList from "./DayStoryboardList";

const items = [
    {
        dayIndex: 0,
        label: "Day 0",
        caption: "A",
        tensionScore: 0.1,
        hasIncidents: false,
        supervisorActivity: 0,
    },
    {
        dayIndex: 1,
        label: "Day 1",
        caption: "B",
        tensionScore: 0.2,
        hasIncidents: true,
        supervisorActivity: 0.1,
    },
];

describe("DayStoryboardList", () => {
    // keep DOM clean between tests
    afterEach(() => cleanup());

    it("renders one strip per item", () => {
        render(
            <DayStoryboardList
                items={items}
                selectedDayIndex={0}
                onSelectDay={vi.fn()}
            />,
        );

        // adjust these test IDs if your strip component uses a different pattern
        expect(screen.getByTestId("day-storyboard-strip-0")).toBeTruthy();
        expect(screen.getByTestId("day-storyboard-strip-1")).toBeTruthy();
    });

    it("applies selected state via data-selected attribute", () => {
        render(
            <DayStoryboardList
                items={items}
                selectedDayIndex={1}
                onSelectDay={vi.fn()}
            />,
        );

        const strip0 = screen.getByTestId("day-storyboard-strip-0");
        const strip1 = screen.getByTestId("day-storyboard-strip-1");

        expect(strip0.getAttribute("data-selected")).not.toBe("true");
        expect(strip1.getAttribute("data-selected")).toBe("true");
    });

    it("calls onSelectDay with the clicked dayIndex", () => {
        const handleSelect = vi.fn();

        render(
            <DayStoryboardList
                items={items}
                selectedDayIndex={0}
                onSelectDay={handleSelect}
            />,
        );

        fireEvent.click(screen.getByTestId("day-storyboard-strip-1"));

        expect(handleSelect).toHaveBeenCalledTimes(1);
        expect(handleSelect).toHaveBeenCalledWith(1);
    });

    it("renders no strips when items is empty", () => {
        render(
            <DayStoryboardList
                items={[]}
                selectedDayIndex={null}
                onSelectDay={vi.fn()}
            />,
        );

        expect(screen.queryAllByTestId(/day-storyboard-strip/)).toHaveLength(0);
    });
});
