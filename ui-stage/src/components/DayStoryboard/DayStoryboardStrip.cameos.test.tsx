// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, screen, within, fireEvent } from "@testing-library/react";
import DayStoryboardStrip from "./DayStoryboardStrip";
import type { DayStoryboardItemViewModel } from "../../vm/dayStoryboardVm";

function makeItem(): DayStoryboardItemViewModel {
  return {
    dayIndex: 2,
    label: "Day 2",
    caption: "A calm day",
    tensionScore: 0.2,
    hasIncidents: false,
    supervisorActivity: 0,
    narrativeLane: [],
    agentCameos: [
      { name: "Ava", roleLabel: "ops", vibeColorKey: "teal", stressTier: "mid", hasAttribution: true },
      { name: "Bob", roleLabel: "tech", vibeColorKey: "green", stressTier: "low", hasAttribution: false },
      { name: "Nia", roleLabel: "supervisor", vibeColorKey: "amber", stressTier: "high", hasAttribution: false },
      { name: "Zed", roleLabel: "observer", vibeColorKey: "indigo", stressTier: "low", hasAttribution: false },
    ],
    agentCameoOverflowCount: 1,
    sparklinePoints: [0.1, 0.2],
    tensionBandClass: "tensionLow",
  };
}

describe("DayStoryboardStrip — agent cameos", () => {
  it("renders up to 3 cameo avatars and an overflow pill with aria-labels, and cameo click does not call onSelect", () => {
    const item = makeItem();
    const onClick = vi.fn();
    const onSelect = vi.fn();
    const { container } = render(
      <DayStoryboardStrip item={item} isSelected={false} onSelect={onSelect} onClickCameo={onClick} />
    );

    const cameoCluster = within(container).getByLabelText(/Agent cameos for Day 2/i);
    // 3 avatars via shared data-testid from AgentAvatar
    const avatars = within(cameoCluster).getAllByTestId("agent-avatar-v1");
    expect(avatars.length).toBe(3);
    // Overflow pill shows +1
    expect(within(cameoCluster).getByText("+1")).toBeTruthy();

    // Buttons have correct aria-label and are clickable
    const btn = within(cameoCluster).getByRole("button", { name: /View Ava's view of Day 2/i });
    fireEvent.click(btn);
    expect(onClick).toHaveBeenCalledWith(2, "Ava");
    expect(onSelect).not.toHaveBeenCalled();
  });
});
