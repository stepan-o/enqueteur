// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AppRouter from "../AppRouter";

describe("Nav rail navigation", () => {
  it("clicking nav links navigates between routes", () => {
    const { getByText, queryByText, getByRole, queryByRole } = render(
      <MemoryRouter initialEntries={["/episodes"]}>
        <AppRouter />
      </MemoryRouter>
    );

    // On /episodes initially
    expect(getByRole("heading", { name: /Episodes/i })).toBeTruthy();

    // Click Agents
    fireEvent.click(getByText("Agents"));
    expect(getByText(/Agents \(Coming Soon\)/)).toBeTruthy();
    expect(queryByRole("heading", { name: /Episodes/i })).toBeFalsy();

    // Click Settings
    fireEvent.click(getByText("Settings"));
    expect(getByText(/Settings \(Coming Soon\)/)).toBeTruthy();
  });
});
