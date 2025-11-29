// @vitest-environment jsdom
import { describe, it, expect, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import AgentAvatar from "./AgentAvatar";

afterEach(() => cleanup());

describe("AgentAvatar v2", () => {
  it("renders circular SVG with ring and blob and a11y label", () => {
    const { getByRole, container, getAllByTestId } = render(
      <AgentAvatar name="Ava" vibeColorKey="teal" stressTier="medium" />
    );
    const img = getByRole("img", { name: /Agent avatar for Ava/i });
    expect(img).toBeTruthy();
    // data-testid kept for stability
    const testEl = getAllByTestId("agent-avatar-v1")[0];
    expect(testEl).toBeTruthy();
    // ensure ring and blob exist
    expect(container.querySelector("circle")).toBeTruthy();
    expect(container.querySelector("path")).toBeTruthy();
  });

  it("applies vibe and stress classes", () => {
    const { rerender, getByTestId } = render(
      <AgentAvatar name="Zed" vibeColorKey="indigo" stressTier="high" />
    );
    const el = getByTestId("agent-avatar-v1");
    expect(el.className).toMatch(/vibe-indigo/);
    expect(el.className).toMatch(/stress-high/);

    rerender(<AgentAvatar name="Zed" vibeColorKey="green" stressTier="cooldown" />);
    expect(el.className).toMatch(/vibe-green/);
    expect(el.className).toMatch(/stress-cooldown/);
  });

  it("gracefully handles missing name and undefined props", () => {
    const { getByRole } = render(<AgentAvatar />);
    const img = getByRole("img", { name: /Agent avatar/i });
    expect(img).toBeTruthy();
  });
});
