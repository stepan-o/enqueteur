import type { StageEpisode, StageDay } from "../types/stage";
import type { EpisodeViewModel } from "./episodeVm";

export interface AgentViewModel {
  name: string;
  role: string;
  stressStart: number;
  stressEnd: number;
  stressDelta: number;
  guardrailTotal: number;
  contextTotal: number;
  visual: string;
  vibe: string;
  tagline: string;
  /** Era II — Phase 3A: visual identity fields (optional, additive) */
  vibeColorKey?: "teal" | "indigo" | "green" | "amber" | "neutral";
  stressTier?: "none" | "medium" | "high" | "cooldown";
  /** Safe, deterministic one-liner for AgentCard v2 */
  displayTagline?: string;
  /** Phase 3B optional panel fields (computed defensively) */
  avgStress?: number;
  latestAttributionCause?: string | null;
  sparkPoints?: string; // SVG polyline points for stress across days
}

export function buildAgentViews(ep: StageEpisode): AgentViewModel[] {
  const list: AgentViewModel[] = Object.entries(ep.agents).map(([name, a]) => {
    const start = a.stress_start ?? 0;
    const end = a.stress_end ?? 0;
    const delta = end - start;
    const role = (a.role || "").toLowerCase();

    // Heuristic mapping: role -> vibeColorKey
    let vibeColor: AgentViewModel["vibeColorKey"] = "neutral";
    if (/(supervisor|lead|manager|overseer)/.test(role)) vibeColor = "amber";
    else if (/(primary|delta|optimizer|operator|actor)/.test(role)) vibeColor = "teal";
    else if (/(observer|monitor|watch|analyst|analysis|reflect)/.test(role)) vibeColor = "indigo";
    else if (/(coordinator|support|helper|ops)/.test(role)) vibeColor = "green";

    // Stress tiering – defensive thresholds
    const stressTier: AgentViewModel["stressTier"] = ((): AgentViewModel["stressTier"] => {
      if (delta < 0) return "cooldown"; // any easing counts as cooldown for v3A UX
      const endAbs = Math.max(0, Math.min(1, end));
      if (endAbs >= 0.66 || delta >= 0.4) return "high";
      if (endAbs >= 0.3 || delta >= 0.15) return "medium";
      return "none";
    })();

    // Tagline fallback
    const directTagline = a.tagline && String(a.tagline).trim();
    let displayTagline: string = directTagline || "";
    if (!displayTagline) {
      // build generic from role
      if (/supervisor|lead/.test(role)) displayTagline = "Analytic supervisor";
      else if (/operator|primary|optimizer/.test(role)) displayTagline = "Primary operator";
      else if (/observer|analyst/.test(role)) displayTagline = "Reflective observer";
      else if (/coordinator|support|ops/.test(role)) displayTagline = "Support coordinator";
      else displayTagline = "System agent";
    }
    return {
      name: a.name || name,
      role: a.role,
      stressStart: start,
      stressEnd: end,
      stressDelta: delta,
      guardrailTotal: a.guardrail_total,
      contextTotal: a.context_total,
      visual: a.visual,
      vibe: a.vibe,
      tagline: a.tagline,
      vibeColorKey: vibeColor,
      stressTier,
      displayTagline,
    };
  });

  // Stable ordering for UI rendering
  list.sort((a, b) => a.name.localeCompare(b.name));
  return list;
}

/**
 * Phase 3B — Build AgentViewModels enriched for the EpisodeAgentsPanel from an EpisodeViewModel.
 * Adds avgStress, latestAttributionCause, and sparkPoints while preserving identity fields.
 * Always sorts by agent name for UI stability.
 */
export function buildPanelAgents(vm: EpisodeViewModel): AgentViewModel[] {
  const raw = vm?._raw as StageEpisode | undefined;
  if (!raw) return [];
  const base = buildAgentViews(raw);

  // Pre-extract day agent stats for fast access
  const days: StageDay[] = Array.isArray(raw.days) ? raw.days : [];

  function computeAvg(name: string): number {
    let sum = 0;
    let count = 0;
    for (const d of days) {
      const a = d.agents?.[name as keyof typeof d.agents] as any;
      const v = a && Number.isFinite(a.avg_stress) ? (a.avg_stress as number) : 0;
      sum += v;
      count += 1;
    }
    return count > 0 ? sum / count : 0;
  }

  function latestCause(name: string): string | null {
    let last: string | null = null;
    for (const d of days) {
      const a = d.agents?.[name as keyof typeof d.agents] as any;
      const cause = a && typeof a.attribution_cause === "string" ? a.attribution_cause : null;
      if (cause) last = cause;
    }
    return last;
  }

  function buildSpark(name: string, width = 60, height = 18): string {
    const values: number[] = days
      .map((d) => d.agents?.[name as keyof typeof d.agents])
      .map((a: any) => (a && Number.isFinite(a.avg_stress) ? (a.avg_stress as number) : 0)) as number[];
    const pts = values.length === 1 ? [values[0], values[0]] : values;
    const n = pts.length;
    if (n === 0) return "";
    const step = n > 1 ? width / (n - 1) : 0;
    const toY = (v: number) => {
      const clamped = Math.max(0, Math.min(1, v || 0));
      return (1 - clamped) * height;
    };
    const coords: string[] = [];
    for (let i = 0; i < n; i++) {
      const x = i * step;
      const y = toY(pts[i]);
      coords.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    }
    return coords.join(" ");
  }

  const enriched = base.map((a) => ({
    ...a,
    avgStress: computeAvg(a.name),
    latestAttributionCause: latestCause(a.name),
    sparkPoints: buildSpark(a.name),
  }));
  enriched.sort((a, b) => a.name.localeCompare(b.name));
  return enriched;
}
