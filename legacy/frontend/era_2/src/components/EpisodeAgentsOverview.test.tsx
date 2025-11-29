// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, within } from "@testing-library/react";
import EpisodeAgentsOverview from "./EpisodeAgentsOverview";
import type { AgentViewModel } from "../vm/agentVm";

describe("EpisodeAgentsOverview", () => {
  const agentsUnsorted: AgentViewModel[] = [
    {
      name: "Delta",
      role: "optimizer",
      stressStart: 0.42,
      stressEnd: 0.09,
      stressDelta: -0.33,
      guardrailTotal: 0,
      contextTotal: 0,
      visual: "delta",
      vibe: "calm",
      tagline: ""
    },
    {
      name: "Ava",
      role: "ops",
      stressStart: 0.10,
      stressEnd: 0.20,
      stressDelta: 0.10,
      guardrailTotal: 0,
      contextTotal: 0,
      visual: "ava",
      vibe: "focused",
      tagline: ""
    },
  ];

  it("renders AgentCards in alphabetical order with avatar, name, role, and tagline", () => {
    const { container, getByText } = render(
      <EpisodeAgentsOverview agents={agentsUnsorted} />
    );

    // Order: Ava first, then Delta
    const list = within(container).getAllByRole("listitem");
    expect(list.length).toBe(2);
    expect(list[0].textContent || "").toMatch(/^Ava/);
    expect(list[1].textContent || "").toMatch(/^Delta/);

    // Role is visible (no specific prefix required now)
    expect(getByText(/ops/i)).toBeTruthy();

    // Avatars render with data-testid marker (kept same as v1 for stability)
    const avatars = within(container).getAllByTestId("agent-avatar-v1");
    expect(avatars.length).toBe(2);
    // sizing should be lg in overview
    expect(avatars[0].getAttribute("data-size")).toBe("lg");

    // Tagline fallback should render even if empty provided
    expect(within(list[0]).getByText(/System agent|tagline/i)).toBeTruthy();
  });

  it("handles empty list gracefully", () => {
    const { getByText, container } = render(
      <EpisodeAgentsOverview agents={[]} />
    );
    expect(getByText(/No agents recorded for this episode/i)).toBeTruthy();
    // Scope queries to this render's container to avoid bleed from prior tests
    expect(within(container).queryAllByRole("listitem").length).toBe(0);
  });
});
