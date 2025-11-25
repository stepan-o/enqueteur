// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import EpisodeNavigator from "./EpisodeNavigator";

describe("EpisodeNavigator", () => {
  it("renders with title, current block, and three dots", () => {
    render(<EpisodeNavigator currentEpisodeId={"ep-abcdef123456"} currentEpisodeIndex={3} />);

    // Title and root
    expect(screen.getByRole("heading", { name: /Episode Navigator/i })).toBeTruthy();
    expect(screen.getByTestId("episode-navigator")).toBeTruthy();

    // Current block with index
    const current = screen.getByTestId("episode-nav-current");
    expect(current).toBeTruthy();
    expect(within(current).getByText(/#3/)).toBeTruthy();

    // Dots presence
    expect(screen.getByTestId("episode-nav-dot-prev")).toBeTruthy();
    expect(screen.getByTestId("episode-nav-dot-current")).toBeTruthy();
    expect(screen.getByTestId("episode-nav-dot-next")).toBeTruthy();
  });

  it("truncates long IDs in visible text but keeps full value in title", () => {
    const id = "ep-abcdefghijklmnopqrstuvwxyz";
    const { container } = render(
      <EpisodeNavigator currentEpisodeId={id} currentEpisodeIndex={1} />
    );

    const current = within(container).getByTestId("episode-nav-current");
    const idSpan = within(current).getByTitle(id);
    expect(idSpan).toBeTruthy();
    // Text should be truncated (first 6 chars + …)
    expect(idSpan.textContent).toBe(`${id.slice(0, 6)}…`);
  });

  it("handles null id by omitting the id span while showing index", () => {
    const { container } = render(
      <EpisodeNavigator currentEpisodeId={null} currentEpisodeIndex={7} />
    );

    const current = within(container).getByTestId("episode-nav-current");
    expect(within(current).getByText(/#7/)).toBeTruthy();
    // There should be no element with a title attribute in this block
    expect(within(current).queryByTitle(/.*/)).toBeNull();
  });
});
