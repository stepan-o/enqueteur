// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import AgentBeliefMiniPanel from "./AgentBeliefMiniPanel";

describe("AgentBeliefMiniPanel", () => {
  it("renders belief text and what happened summary", () => {
    render(
      <AgentBeliefMiniPanel dayIndex={1} agentName="Ava" beliefText="network outage" whatHappened="Tension 0.44 • incidents 3 • supervisor 0" />
    );
    expect(screen.getByRole("group", { name: /Belief versus outcome for Ava on Day 1/i })).toBeTruthy();
    expect(screen.getByText(/How Ava saw it/i)).toBeTruthy();
    expect(screen.getByText(/network outage/i)).toBeTruthy();
    expect(screen.getByText(/What actually happened/i)).toBeTruthy();
    expect(screen.getByText(/Tension 0.44/i)).toBeTruthy();
  });

  it("falls back when belief text missing", () => {
    render(
      <AgentBeliefMiniPanel dayIndex={0} agentName="Bob" beliefText={null} whatHappened="Tension 0.10 • incidents 0 • supervisor 0" />
    );
    expect(screen.getByText(/No explicit belief recorded for this day/i)).toBeTruthy();
  });
});
