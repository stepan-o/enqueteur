// @vitest-environment jsdom
import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import EpisodeStoryPanel from "./EpisodeStoryPanel";
import type { EpisodeStoryViewModel } from "../vm/storyVm";

describe("EpisodeStoryPanel", () => {
  // Ensure DOM isolation between tests to avoid cross-test text collisions
  afterEach(() => {
    cleanup();
  });

  it("renders empty state when all story fields are empty/null", () => {
    const story: EpisodeStoryViewModel = {
      storyArc: null,
      longMemory: null,
      topLevelNarrative: [],
    };

    render(<EpisodeStoryPanel story={story} />);
    expect(screen.getByText(/No story arc or long-memory data/i)).toBeTruthy();
  });

  it("renders JSON for story arc when present", () => {
    const story: EpisodeStoryViewModel = {
      storyArc: { arc: "Rising", beats: ["start", "conflict"] },
      longMemory: null,
      topLevelNarrative: [],
    };

    render(<EpisodeStoryPanel story={story} />);
    // Target the <h3> heading specifically to avoid substring collisions
    expect(screen.getByRole("heading", { name: /Story Arc/i })).toBeTruthy();
    // The pretty-printed JSON should appear in the <pre>
    expect(screen.getByText(/"arc": "Rising"/)).toBeTruthy();
  });

  it("renders narrative blocks when present", () => {
    const story: EpisodeStoryViewModel = {
      storyArc: null,
      longMemory: null,
      topLevelNarrative: [
        { block_id: "b1", kind: "recap", text: "Day 0 overview", day_index: 0, agent_name: null, tags: ["recap"] },
        { block_id: "b2", kind: "beat", text: "A thing happened", day_index: 1, agent_name: null, tags: ["beat"] },
      ],
    };

    render(<EpisodeStoryPanel story={story} />);
    expect(screen.getByText(/Top-Level Narrative/i)).toBeTruthy();
    expect(screen.getByText(/recap/i)).toBeTruthy();
    expect(screen.getByText(/Day 0 overview/i)).toBeTruthy();
    // Use more specific selector for 'beat' to avoid matching JSON text in <pre>
    expect(screen.getAllByText(/beat/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/A thing happened/i)).toBeTruthy();
  });
});
