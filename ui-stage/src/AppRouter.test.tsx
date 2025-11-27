// @vitest-environment jsdom
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AppRouter from "./AppRouter";

// For route tests where StageView/LatestEpisodeView load episodes, passthrough VM and mock API
vi.mock("./vm/episodeVm", () => ({
  buildEpisodeView: (x: any) => x,
}));
import * as api from "./api/episodes";

describe("AppRouter routes", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });
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

  it("renders StageView at root / with Stage map and details panel", async () => {
    const vm: any = {
      id: "ep-root",
      runId: "run-root",
      index: 0,
      stageVersion: 1,
      days: [
        { index: 0, tensionScore: 0.2, totalIncidents: 0, perceptionMode: "n", supervisorActivity: 0 },
      ],
      tensionTrend: [0.2],
      agents: [],
      story: { storyArc: null, longMemory: null, topLevelNarrative: [] },
      _raw: {
        episode_id: "ep-root",
        run_id: "run-root",
        episode_index: 0,
        stage_version: 1,
        tension_trend: [0.2],
        days: [
          {
            day_index: 0,
            perception_mode: "n",
            tension_score: 0.2,
            total_incidents: 0,
            supervisor_activity: 0,
            narrative: [],
            agents: {},
          },
        ],
        agents: {},
        story_arc: null,
        narrative: [],
        long_memory: null,
        character_defs: null,
      },
    };
    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(vm);

    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRouter />
      </MemoryRouter>
    );

    const region = await screen.findByRole("region", { name: /Stage map/i });
    expect(region).toBeTruthy();
    const mapGroup = within(region).getByRole("group", { name: /Stage map/i });
    expect(mapGroup).toBeTruthy();
    // Details panel is present
    expect(await screen.findByLabelText(/Stage details panel/i)).toBeTruthy();
  });

  it("renders LatestEpisodeView at /episodes/:id", async () => {
    const vm: any = {
      id: "ep-123",
      runId: "run-123",
      index: 1,
      stageVersion: 1,
      days: [
        { index: 0, tensionScore: 0.1, totalIncidents: 0, perceptionMode: "n", supervisorActivity: 0 },
        { index: 1, tensionScore: 0.6, totalIncidents: 1, perceptionMode: "n", supervisorActivity: 0 },
      ],
      tensionTrend: [0.1, 0.6],
      agents: [],
      story: { storyArc: null, longMemory: null, topLevelNarrative: [] },
      _raw: {
        episode_id: "ep-123",
        run_id: "run-123",
        episode_index: 1,
        stage_version: 1,
        tension_trend: [0.1, 0.6],
        days: [
          { day_index: 0, perception_mode: "n", tension_score: 0.1, total_incidents: 0, supervisor_activity: 0, agents: {}, narrative: [] },
          { day_index: 1, perception_mode: "n", tension_score: 0.6, total_incidents: 1, supervisor_activity: 0, agents: {}, narrative: [] },
        ],
        agents: {}, story_arc: null, narrative: [], long_memory: null, character_defs: null,
      },
    };
    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(vm);

    render(
      <MemoryRouter initialEntries={["/episodes/ep-123"]}>
        <AppRouter />
      </MemoryRouter>
    );
    // It should render the Latest view header content; Episode Agents Overview section appears
    expect(await screen.findByText(/Episode Agents Overview/i)).toBeTruthy();
  });

  it("renders StageView at /episodes/:id/stage", async () => {
    const vm: any = {
      id: "ep-123",
      runId: "run-123",
      index: 1,
      stageVersion: 1,
      days: [
        { index: 0, tensionScore: 0.1, totalIncidents: 0, perceptionMode: "n", supervisorActivity: 0 },
        { index: 1, tensionScore: 0.6, totalIncidents: 1, perceptionMode: "n", supervisorActivity: 0 },
      ],
      tensionTrend: [0.1, 0.6],
      agents: [],
      story: { storyArc: null, longMemory: null, topLevelNarrative: [] },
      _raw: {
        episode_id: "ep-123",
        run_id: "run-123",
        episode_index: 1,
        stage_version: 1,
        tension_trend: [0.1, 0.6],
        days: [
          { day_index: 0, perception_mode: "n", tension_score: 0.1, total_incidents: 0, supervisor_activity: 0, agents: {}, narrative: [] },
          { day_index: 1, perception_mode: "n", tension_score: 0.6, total_incidents: 1, supervisor_activity: 0, agents: {}, narrative: [] },
        ],
        agents: {}, story_arc: null, narrative: [], long_memory: null, character_defs: null,
      },
    };
    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(vm);

    render(
      <MemoryRouter initialEntries={["/episodes/ep-123/stage"]}>
        <AppRouter />
      </MemoryRouter>
    );
    // StageMap may render more than once during initial mount in StrictMode/tests; accept >= 1
    const mapGroups = await screen.findAllByTestId("stage-map-group");
    expect(mapGroups.length).toBeGreaterThan(0);
  });
});
