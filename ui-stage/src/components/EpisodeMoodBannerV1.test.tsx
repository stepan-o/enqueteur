// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import EpisodeMoodBannerV1 from "./EpisodeMoodBannerV1";

const mood = {
  label: "Building Pressure",
  icon: "🔺",
  tensionClass: "medium" as const,
  summaryLine: "Systems show strain under load.",
};

describe("EpisodeMoodBannerV1", () => {
  it("renders icon, label, and summary with correct aria-label", () => {
    const { container } = render(<EpisodeMoodBannerV1 mood={mood} />);
    // Icon role="img" with aria-label clarifying episode-wide arc
    const icon = screen.getByRole("img", { name: /Episode arc mood:/i });
    expect(icon).toBeTruthy();
    expect(icon.textContent).toBe("🔺");
    // Label and summary visible
    expect(screen.getByText(/Building Pressure/)).toBeTruthy();
    expect(screen.getByText(/Systems show strain under load/)).toBeTruthy();
    // Mood class applied on banner
    const banner = screen.getByTestId("episode-mood-banner");
    expect((banner as HTMLElement).className).toMatch(/medium/);
    // Snapshot stable
    expect(container.firstChild).toMatchSnapshot();
  });
});
