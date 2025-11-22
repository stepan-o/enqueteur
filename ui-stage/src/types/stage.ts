// StageEpisode v1 types — kept 1:1 with backend JSON

export interface StageEpisode {
  stage_version: number;
  episode_id: string;
  run_id: string;
  episode_index: number;
  tension_trend: number[];
  days: StageDay[];
  agents: Record<string, StageAgentSummary>;
  narrative?: any;
}

export interface StageDay {
  day_index: number;
  tension_score: number;
  total_incidents: number;
  perception_mode: string;
  supervisor_activity: number;
  agents: Record<string, StageAgentDayView>;
}

export interface StageAgentSummary {
  stress_start: number;
  stress_end: number;
  guardrail_total: number;
  context_total: number;
}

export interface StageAgentDayView {
  avg_stress: number;
  guardrail_count: number;
  context_count: number;
  emotional_read?: string | null;
  attribution_cause?: string | null;
}
