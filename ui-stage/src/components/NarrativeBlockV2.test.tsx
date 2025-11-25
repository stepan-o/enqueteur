// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import NarrativeBlockV2 from "./NarrativeBlockV2";
import type { StageNarrativeBlock } from "../types/stage";

describe("NarrativeBlockV2", () => {
  it("renders with icon, text, tags, and meta with mood tint", () => {
    const block: StageNarrativeBlock = {
      block_id: "b1",
      kind: "recap",
      text: "A warm recap of the day with subtle conflict noted.",
      day_index: 1,
      agent_name: "Ari",
      tags: ["recap", "conflict"],
    };

    const { container, getByTestId } = render(<NarrativeBlockV2 block={block} />);
    const root = getByTestId("narrative-block");
    expect(root).toBeTruthy();
    // Snapshot the rendered HTML structure (CSS classes may vary but structure should be stable)
    expect(container.firstChild).toMatchSnapshot();
  });
});
