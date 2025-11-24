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

  it("renders all agents in alphabetical order with role and stress stats", () => {
    const { container, getByText } = render(
      <EpisodeAgentsOverview agents={agentsUnsorted} />
    );

    // Order: Ava first, then Delta
    const list = within(container).getAllByRole("listitem");
    expect(list.length).toBe(2);
    expect(list[0].textContent || "").toMatch(/^Ava/);
    expect(list[1].textContent || "").toMatch(/^Delta/);

    // Role and stress delta formatting
    expect(getByText(/role ops/)).toBeTruthy();
    // Contains delta and start/end values
    const text = container.textContent || "";
    expect(text).toMatch(/Stress Δ: -0.33/);
    expect(text).toMatch(/start 0.42/);
    expect(text).toMatch(/end 0.09/);
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
