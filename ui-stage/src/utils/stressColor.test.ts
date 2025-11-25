import { describe, it, expect } from "vitest";
import { stressColor } from "./stressColor";

describe("stressColor", () => {
  it("maps low range (<=0.15) to blue", () => {
    expect(stressColor(0.0)).toBe("#4FA3FF");
    expect(stressColor(0.10)).toBe("#4FA3FF");
    expect(stressColor(0.15)).toBe("#4FA3FF");
  });

  it("maps <=0.30 to yellow", () => {
    expect(stressColor(0.16)).toBe("#FFD93D");
    expect(stressColor(0.25)).toBe("#FFD93D");
    expect(stressColor(0.30)).toBe("#FFD93D");
  });

  it("maps <=0.50 to orange", () => {
    expect(stressColor(0.31)).toBe("#FF9F1C");
    expect(stressColor(0.45)).toBe("#FF9F1C");
    expect(stressColor(0.50)).toBe("#FF9F1C");
  });

  it("maps >0.50 to red", () => {
    expect(stressColor(0.51)).toBe("#E44040");
    expect(stressColor(0.80)).toBe("#E44040");
    expect(stressColor(1.0)).toBe("#E44040");
  });

  it("clamps invalid inputs to blue", () => {
    // @ts-expect-error intentional invalids
    expect(stressColor(null)).toBe("#4FA3FF");
    // @ts-expect-error intentional invalids
    expect(stressColor(undefined)).toBe("#4FA3FF");
    expect(stressColor(Number.NaN as unknown as number)).toBe("#4FA3FF");
  });
});
