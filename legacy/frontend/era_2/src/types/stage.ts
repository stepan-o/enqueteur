// StageEpisode v1 types — kept 1:1 with backend JSON (stage_episode.py)

// Helper types for generic mappings used by backend (Mapping[str, Any])
export type AnyDict = Record<string, unknown>;

export interface StageNarrativeBlock {
  block_id: string | null;
  kind: string; // e.g., "recap", "beat", "aside"
  text: string;
  day_index: number | null;
  agent_name: string | null;
  tags: string[];
}

export interface StageAgentTraits {
  // Only present keys are included in JSON; each value is 0..1.
  resilience?: number;
  caution?: number;
  agency?: number;
  trust_supervisor?: number;
  variance?: number;
}

export interface StageAgentDayView {
  name: string;
  role: string;
  avg_stress: number;
  guardrail_count: number;
  context_count: number;
  emotional_read: AnyDict | null; // optional mapping if available
  attribution_cause: string | null; // "random" | "system" | "self" | "supervisor" (if present)
  narrative: StageNarrativeBlock[];
}

export interface StageDay {
  day_index: number;
  perception_mode: string;
  tension_score: number;
  agents: Record<string, StageAgentDayView>;
  total_incidents: number;
  supervisor_activity: number;
  narrative: StageNarrativeBlock[];
}

export interface StageAgentSummary {
  name: string;
  role: string;
  guardrail_total: number;
  context_total: number;
  stress_start: number | null;
  stress_end: number | null;
  trait_snapshot: StageAgentTraits | null;
  visual: string;
  vibe: string;
  tagline: string;
}

export interface StageEpisode {
  episode_id: string | null;
  run_id: string | null;
  episode_index: number;
  stage_version: number; // defaults to 1 in backend
  tension_trend: number[];

  days: StageDay[];
  agents: Record<string, StageAgentSummary>;

  // Optional narrative/story overlays
  story_arc: AnyDict | null;
  narrative: StageNarrativeBlock[];

  // Optional slow character memory snapshot
  long_memory: Record<string, AnyDict> | null;

  // Convenience/testing: slice of character registry
  character_defs: Record<string, AnyDict> | null;
}
