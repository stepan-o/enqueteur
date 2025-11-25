// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, within } from "@testing-library/react";
import EpisodesIndexView, { buildMockEpisodeList } from "./EpisodesIndexView";

describe("EpisodesIndexView", () => {
  it("renders heading and explainer text", () => {
    const { getByRole, getByText } = render(<EpisodesIndexView />);

    expect(getByRole("heading", { name: /Episodes/i })).toBeTruthy();
    expect(
      getByText(/stubbed list; later this will be wired to the backend source of truth/i)
    ).toBeTruthy();
  });

  it("renders mock episodes list with correct row count and sample content", () => {
    const items = buildMockEpisodeList();
    const { container } = render(<EpisodesIndexView />);

    // Count only tbody rows (exclude header)
    const tbody = container.querySelector("tbody") as HTMLElement;
    expect(tbody).toBeTruthy();
    const rows = Array.from(tbody.querySelectorAll("tr"));
    expect(rows.length).toBe(items.length);

    // Spot check: first row includes the expected summary fragment
    const firstRowText = rows[0]?.textContent || "";
    expect(firstRowText).toMatch(/Decompression arc/i);
  });

  it("shows empty state when no episodes are available", () => {
    const { getByText, container } = render(<EpisodesIndexView items={[]} />);
    expect(getByText(/No episodes available yet/i)).toBeTruthy();
    // And ensure the table is not rendered within this view
    expect(within(container).queryByRole("table")).toBeNull();
  });
});
