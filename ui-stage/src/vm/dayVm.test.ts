import { describe, it, expect, expectTypeOf } from "vitest";
import { buildDayViews, type DayViewModel } from "./dayVm";
import type { StageDay } from "../types/stage";

describe("buildDayViews", () => {
  const days: StageDay[] = [
    {
      day_index: 0,
      perception_mode: "normal",
      tension_score: 0.1,
      agents: {},
      total_incidents: 1,
      supervisor_activity: 0.05,
      narrative: [],
    },
    {
      day_index: 1,
      perception_mode: "alert",
      tension_score: 0.6,
      agents: {},
      total_incidents: 3,
      supervisor_activity: 0.2,
      narrative: [],
    },
    {
      day_index: 2,
      perception_mode: "normal",
      tension_score: 0.3,
      agents: {},
      total_incidents: 0,
      supervisor_activity: 0.0,
      narrative: [],
    },
  ];

  it("maps fields 1:1 and preserves order", () => {
    const vms = buildDayViews(days);
    expectTypeOf<DayViewModel[]>().toMatchTypeOf(vms);

    expect(vms.length).toBe(3);
    expect(vms[0]).toEqual({
      index: 0,
      perceptionMode: "normal",
      tensionScore: 0.1,
      totalIncidents: 1,
      supervisorActivity: 0.05,
    });
    expect(vms[1].index).toBe(1);
    expect(vms[1].perceptionMode).toBe("alert");
    expect(vms[2].tensionScore).toBeCloseTo(0.3, 5);
  });
});
