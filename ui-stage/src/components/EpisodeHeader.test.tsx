// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import EpisodeHeader from "./EpisodeHeader";
import type { EpisodeViewModel } from "../vm/episodeVm";

describe("EpisodeHeader", () => {
  const episode: EpisodeViewModel = {
    id: "ep-99",
    runId: "run-abc",
    index: 3,
    stageVersion: 1,
    days: [],
    agents: [],
    tensionTrend: [0.1, 0.2],
  };

  it("renders core episode metadata", () => {
    render(<EpisodeHeader episode={episode} />);

    expect(screen.getByText(/Episode:/)).toBeTruthy();
    expect(screen.getByText(/ep-99/)).toBeTruthy();

    expect(screen.getByText(/Run:/)).toBeTruthy();
    expect(screen.getByText(/run-abc/)).toBeTruthy();

    const daysLabel = screen.getByText(/Days:/);
    expect(daysLabel).toBeTruthy();
    expect(daysLabel.parentElement?.textContent || "").toMatch(/Days:\s*0/);

    expect(screen.getByText(/Stage Version:/)).toBeTruthy();
  });
});
