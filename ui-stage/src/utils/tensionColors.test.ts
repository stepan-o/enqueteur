import { describe, it, expect } from "vitest";
import { tensionColor } from "./tensionColors";

describe("tensionColor", () => {
  it("maps low range (<=0.15) to blue", () => {
    expect(tensionColor(0.0)).toBe("#4FA3FF");
    expect(tensionColor(0.10)).toBe("#4FA3FF");
    expect(tensionColor(0.15)).toBe("#4FA3FF");
  });

  it("maps <=0.30 to yellow", () => {
    expect(tensionColor(0.16)).toBe("#FFD93D");
    expect(tensionColor(0.25)).toBe("#FFD93D");
    expect(tensionColor(0.30)).toBe("#FFD93D");
  });

  it("maps <=0.50 to orange", () => {
    expect(tensionColor(0.31)).toBe("#FF9F1C");
    expect(tensionColor(0.45)).toBe("#FF9F1C");
    expect(tensionColor(0.50)).toBe("#FF9F1C");
  });

  it("maps >0.50 to red", () => {
    expect(tensionColor(0.51)).toBe("#E44040");
    expect(tensionColor(0.80)).toBe("#E44040");
    expect(tensionColor(1.0)).toBe("#E44040");
  });

  it("clamps invalid inputs to blue", () => {
    // @ts-expect-error intentional invalids
    expect(tensionColor(null)).toBe("#4FA3FF");
    // @ts-expect-error intentional invalids
    expect(tensionColor(undefined)).toBe("#4FA3FF");
    // NaN
    expect(tensionColor(Number.NaN as unknown as number)).toBe("#4FA3FF");
  });
});
