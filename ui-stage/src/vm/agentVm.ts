import type { StageEpisode } from "../types/stage";

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
