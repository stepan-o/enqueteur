// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AppRouter from "./AppRouter";

describe("AppRouter routes", () => {
  it("renders Agents placeholder at /agents", () => {
    const { getByText } = render(
      <MemoryRouter initialEntries={["/agents"]}>
        <AppRouter />
      </MemoryRouter>
    );

    expect(getByText(/Agents \(Coming Soon\)/)).toBeTruthy();
  });

  it("renders Settings placeholder at /settings", () => {
    const { getByText } = render(
      <MemoryRouter initialEntries={["/settings"]}>
        <AppRouter />
      </MemoryRouter>
    );

    expect(getByText(/Settings \(Coming Soon\)/)).toBeTruthy();
  });

  it("renders Episodes index at /episodes", () => {
    const { getByRole, getByText } = render(
      <MemoryRouter initialEntries={["/episodes"]}>
        <AppRouter />
      </MemoryRouter>
    );

    // Heading present
    expect(getByRole("heading", { name: /Episodes/i })).toBeTruthy();
    // Mock content present (summary fragment)
    expect(getByText(/stubbed list; later this will be wired/i)).toBeTruthy();
  });
});
