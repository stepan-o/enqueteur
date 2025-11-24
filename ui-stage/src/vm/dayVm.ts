import type { StageDay } from "../types/stage";

export interface DayViewModel {
  index: number;
  tensionScore: number;
  totalIncidents: number;
  perceptionMode: string;
  supervisorActivity: number;
}

export function buildDayViews(days: StageDay[]): DayViewModel[] {
  return days.map((d) => ({
    index: d.day_index,
    tensionScore: d.tension_score,
    totalIncidents: d.total_incidents,
    perceptionMode: d.perception_mode,
    supervisorActivity: d.supervisor_activity,
  }));
}
