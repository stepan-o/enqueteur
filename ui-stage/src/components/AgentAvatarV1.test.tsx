// @vitest-environment jsdom
import { describe, it, expect, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import AgentAvatarV1 from "./AgentAvatarV1";
import { cleanup } from "@testing-library/react";

afterEach(() => cleanup());

describe("AgentAvatarV1", () => {
  it("renders name initial and accessibility label", () => {
    render(
      <AgentAvatarV1 name="Ava" role="optimizer" vibe="calm" visual="ava" />
    );
    const avatar = screen.getByLabelText("Agent avatar for Ava, role: optimizer");
    expect(avatar).toBeTruthy();
    // initial is rendered as a child text
    expect(avatar.textContent).toContain("A");
  });

  it("applies correct background color for vibe and falls back for unknown", () => {
    const { rerender, unmount } = render(
      <AgentAvatarV1 name="Delta" role="qa" vibe="calm" visual="delta" />
    );
    const el = screen.getByTestId("agent-avatar-v1") as HTMLElement;
    // Inline style should include the CSS var reference
    expect(el.getAttribute("style")).toContain("--lf-vibe-calm");

    // Unmount to avoid multiple avatar instances in the DOM for the next assertion
    unmount();
    render(
      <AgentAvatarV1 name="Echo" role="maintenance" vibe="mystery" visual="echo" />
    );
    const el2 = screen.getByTestId("agent-avatar-v1") as HTMLElement;
    expect(el2.getAttribute("style")).toContain("--lf-vibe-neutral");
  });

  it("includes role mapping via data-role and respects size prop", () => {
    render(
      <AgentAvatarV1 name="Nora" role="analytic" vibe="analytic" visual="nora" size="lg" />
    );
    const el = screen.getByTestId("agent-avatar-v1") as HTMLElement;
    expect(el.getAttribute("data-role")).toContain("analytic");
    expect(el.getAttribute("data-size")).toBe("lg");
  });
});
