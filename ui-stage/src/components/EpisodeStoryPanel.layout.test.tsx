// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import EpisodeStoryPanel from "./EpisodeStoryPanel";
import type { EpisodeStoryViewModel } from "../vm/storyVm";

describe("EpisodeStoryPanel — structured arc layout", () => {
  it("shows muted empty-state when storyArc is null and no narrative/memory", () => {
    const story: EpisodeStoryViewModel = {
      storyArc: null,
      longMemory: null,
      topLevelNarrative: [],
    };
    render(<EpisodeStoryPanel story={story} />);
    expect(
      screen.getByText(/No story arc or long-memory data for this episode/i)
    ).toBeTruthy();
  });

  it("renders sub-section titles when common arc fields exist (summary, beats)", () => {
    const story: EpisodeStoryViewModel = {
      storyArc: { summary: "A gentle rise.", beats: ["start", { note: "turn" }] },
      longMemory: null,
      topLevelNarrative: [],
    } as any;

    const { container } = render(<EpisodeStoryPanel story={story} />);
    // Main title
    expect(screen.getByRole("heading", { name: /Story Arc/i })).toBeTruthy();
    // Sub-sections added by the improved layout
    expect(screen.getByText(/arc summary/i)).toBeTruthy();
    // 'beats' may appear both as subheader and within JSON; assert at least one instance
    expect(screen.getAllByText(/beats/i).length).toBeGreaterThan(0);
    // Content presence (be tolerant: match anywhere in the rendered text, including <pre>)
    expect((container.textContent || "")).toMatch(/gentle rise/i);
    expect(screen.getAllByText(/start|turn/).length).toBeGreaterThan(0);
  });

  it("matches a stable text snapshot for arc-only render (text-only)", () => {
    const story: EpisodeStoryViewModel = {
      storyArc: { summary: "Rising conflict", beats: ["begin", "conflict", "resolve"] },
      longMemory: null,
      topLevelNarrative: [],
    } as any;

    const { container } = render(<EpisodeStoryPanel story={story} />);
    // Snapshot the textual content to avoid CSS module class name noise
    expect(container.textContent).toMatchInlineSnapshot(
      `"Story Arcarc summaryRising conflictbeatsbeginconflictresolve{\n  \"summary\": \"Rising conflict\",\n  \"beats\": [\n    \"begin\",\n    \"conflict\",\n    \"resolve\"\n  ]\n}"`
    );
  });
});
