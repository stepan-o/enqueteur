// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AppRouter from "../AppRouter";

describe("Nav rail navigation", () => {
  it("clicking nav links navigates between routes", () => {
    const { getByText, queryByText } = render(
      <MemoryRouter initialEntries={["/episodes"]}>
        <AppRouter />
      </MemoryRouter>
    );

    // On /episodes initially
    expect(getByText(/Episodes \(Coming Soon\)/)).toBeTruthy();

    // Click Agents
    fireEvent.click(getByText("Agents"));
    expect(getByText(/Agents \(Coming Soon\)/)).toBeTruthy();
    expect(queryByText(/Episodes \(Coming Soon\)/)).toBeFalsy();

    // Click Settings
    fireEvent.click(getByText("Settings"));
    expect(getByText(/Settings \(Coming Soon\)/)).toBeTruthy();
  });
});
