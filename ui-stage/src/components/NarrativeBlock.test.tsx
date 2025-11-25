// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import NarrativeBlock from "./NarrativeBlock";
import type { StageNarrativeBlock } from "../types/stage";

describe("NarrativeBlock", () => {
  it("renders kind and text", () => {
    const b: StageNarrativeBlock = {
      block_id: "n1",
      kind: "beat",
      text: "A small moment",
      day_index: 0,
      agent_name: null,
      tags: [],
    };

    render(<NarrativeBlock block={b} />);
    expect(screen.getByText(/beat/i)).toBeTruthy();
    expect(screen.getByText(/A small moment/)).toBeTruthy();
  });

  it("renders tags as pill badges when present", () => {
    const b: StageNarrativeBlock = {
      block_id: "n2",
      kind: "aside",
      text: "Tagged bit",
      day_index: 1,
      agent_name: "Ava",
      tags: ["intro", "mood"],
    };
    render(<NarrativeBlock block={b} />);
    const tagsRegion = screen.getByLabelText("tags");
    const text = tagsRegion.textContent || "";
    expect(text).toMatch(/intro/);
    expect(text).toMatch(/mood/);
  });

  it("handles missing tags gracefully", () => {
    const b = {
      block_id: null,
      kind: "recap",
      text: "No tags here",
      day_index: null,
      agent_name: null,
      // @ts-expect-error intentionally omit tags field
    } as unknown as StageNarrativeBlock;

    const { container } = render(<NarrativeBlock block={b} />);
    // No tags container should render
    expect(container.querySelector('[aria-label="tags"]')).toBeNull();
  });

  it("supports optional day_index and agent_name in meta line", () => {
    const b: StageNarrativeBlock = {
      block_id: "n3",
      kind: "beat",
      text: "Meta present",
      day_index: 2,
      agent_name: "Bob",
      tags: [],
    };
    const { container } = render(<NarrativeBlock block={b} />);
    const text = container.textContent || "";
    expect(text).toMatch(/Day 2/);
    expect(text).toMatch(/Agent Bob/);
  });

  it("matches snapshot for stability (text content)", () => {
    const b: StageNarrativeBlock = {
      block_id: "snap-1",
      kind: "supervisor",
      text: "Supervisor checks in periodically",
      day_index: 1,
      agent_name: null,
      tags: ["supervisor", "checkin"],
    };
    const { container } = render(<NarrativeBlock block={b} />);
    // Snapshot only the textual content to avoid CSS module class name noise
    expect((container.firstElementChild as HTMLElement).textContent).toMatchInlineSnapshot(
      `"supervisorSupervisor checks in periodicallysupervisorcheckinDay 1"`
    );
  });
});
