// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, within, fireEvent } from "@testing-library/react";
import EpisodesIndexView, { buildMockEpisodeList } from "./EpisodesIndexView";

// Mock the navigator hook so we can assert navigation behavior
const navigateSpy = vi.fn();
vi.mock("../hooks/useEpisodeNavigator", () => {
  return {
    useEpisodeNavigator: () => ({ navigateToEpisode: navigateSpy }),
  };
});

describe("EpisodesIndexView", () => {
  beforeEach(() => {
    navigateSpy.mockReset();
  });

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

    // The list should be a UL with list items
    const lists = screen.getAllByRole("list", { name: /Episodes list/i });
    expect(lists.length).toBeGreaterThan(0);
    const rows = within(lists[0]).getAllByRole("listitem");
    expect(rows.length).toBe(items.length);

    // Spot check: first row includes the expected summary fragment
    const firstRowText = rows[0]?.textContent || "";
    expect(firstRowText).toMatch(/Decompression arc/i);
  });

  it("clicking View Episode calls navigateToEpisode with the correct id", () => {
    const items = buildMockEpisodeList();
    render(<EpisodesIndexView items={items} />);

    const target = items[1];
    // Select the specific "View Episode <id>" button (may appear multiple times due to double-render in tests)
    const btns = screen.getAllByRole("button", {
      name: new RegExp(`View Episode ${target.id}`),
    });
    expect(btns.length).toBeGreaterThan(0);
    fireEvent.click(btns[0]);

    expect(navigateSpy).toHaveBeenCalledTimes(1);
    expect(navigateSpy).toHaveBeenCalledWith(target.id);
  });

  it("shows empty state when no episodes are available", () => {
    const { getByText, container } = render(<EpisodesIndexView items={[]} />);
    expect(getByText(/No episodes found/i)).toBeTruthy();
    // Ensure the list is not rendered (container-scoped selector for stability)
    expect(container.querySelector('ul[aria-label="Episodes list"]')).toBeNull();
  });

  it("accessibility: section labeled and buttons focusable", () => {
    render(<EpisodesIndexView />);

    // Section label present (regions are landmark role for section with accessible name)
    const sections = screen.getAllByRole("region", { name: /Episodes overview/i });
    expect(sections.length).toBeGreaterThan(0);

    // Buttons have role=button and can receive focus
    const buttons = screen.getAllByRole("button", { name: /View Episode/i });
    expect(buttons.length).toBeGreaterThan(0);
    const first = buttons[0] as HTMLButtonElement;
    first.focus();
    expect(document.activeElement).toBe(first);
  });
});
