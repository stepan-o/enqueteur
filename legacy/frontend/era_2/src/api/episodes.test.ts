import { describe, it, expect, vi, beforeEach, afterEach, expectTypeOf } from "vitest";
import { getLatestEpisode, getEpisodeById } from "./episodes";
import type { StageEpisode } from "../types/stage";

declare const global: any;

describe("episodes API client", () => {
  const minimalEpisode: StageEpisode = {
    episode_id: "ep-1",
    run_id: "run-1",
    episode_index: 0,
    stage_version: 1,
    tension_trend: [],
    days: [],
    agents: {},
    story_arc: null,
    narrative: [],
    long_memory: null,
    character_defs: null,
  };

  beforeEach(() => {
    vi.spyOn(global, "fetch");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("getLatestEpisode returns StageEpisode on success", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => minimalEpisode,
    });

    const result = await getLatestEpisode();
    expect(result).toBeTruthy();
    // Type-level check: result should satisfy StageEpisode
    expectTypeOf(result).toMatchTypeOf<StageEpisode>();
    // Runtime sanity check
    expect(result.episode_id).toBe("ep-1");
  });

  it("getEpisodeById returns StageEpisode on success", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => minimalEpisode,
    });

    const result = await getEpisodeById("ep-123");
    expectTypeOf(result).toMatchTypeOf<StageEpisode>();
    expect(result.stage_version).toBe(1);
  });

  it("throws Error on non-OK status with status code", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Not Found" }),
    });

    await expect(getLatestEpisode()).rejects.toThrow(/HTTP 404/);
  });

  it("throws Error with 'Network error' prefix on fetch failure", async () => {
    (global.fetch as any).mockRejectedValueOnce(new Error("ECONNREFUSED"));
    await expect(getLatestEpisode()).rejects.toThrow(/Network error:/);
  });
});
