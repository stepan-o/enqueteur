import type { EpisodeViewModel } from "./episodeVm";

export interface EpisodeArcMoodViewModel {
  label: string;        // e.g., "Calm Shift", "Minor Escalation", "Building Pressure", "Spike Episode"
  icon: string;         // emoji icon: 🌿, 🔶, 🔺, ⚡
  tensionClass: "calm" | "minor" | "medium" | "spike";
  summaryLine: string;  // one-line capsule
}

function classifyDelta(delta: number): "calm" | "minor" | "medium" | "spike" {
  // Threshold mapping per spec (interpreting last bucket as >= 0.45 → spike)
  if (delta < 0.1) return "calm";
  if (delta < 0.25) return "minor";
  if (delta < 0.45) return "medium";
  return "spike";
}

function labelFor(cls: EpisodeArcMoodViewModel["tensionClass"]): string {
  switch (cls) {
    case "calm":
      return "Calm Shift";
    case "minor":
      return "Minor Escalation";
    case "medium":
      return "Building Pressure";
    case "spike":
      return "Spike Episode";
  }
}

function iconFor(cls: EpisodeArcMoodViewModel["tensionClass"]): string {
  switch (cls) {
    case "calm":
      return "🌿";
    case "minor":
      return "🔶";
    case "medium":
      return "🔺";
    case "spike":
      return "⚡";
  }
}

export function buildEpisodeArcMood(episode: EpisodeViewModel): EpisodeArcMoodViewModel {
  const trend = Array.isArray(episode?.tensionTrend) ? episode.tensionTrend : [];
  const values = trend.filter((n) => Number.isFinite(n)) as number[];

  let delta = 0;
  if (values.length > 0) {
    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;
    for (const v of values) {
      if (v < min) min = v;
      if (v > max) max = v;
    }
    if (min === Number.POSITIVE_INFINITY || max === Number.NEGATIVE_INFINITY) {
      delta = 0;
    } else {
      delta = Math.max(0, max - min);
    }
  }

  const cls = classifyDelta(delta);
  const label = labelFor(cls);
  const icon = iconFor(cls);

  // Summary: first top-level narrative block text if present, else fallback
  const firstText = (episode?.story?.topLevelNarrative && episode.story.topLevelNarrative[0]?.text) || "";
  const summaryLine = firstText.length > 0
    ? firstText
    : "Episode explores subtle shifts in behavior.";

  return { label, icon, tensionClass: cls, summaryLine };
}
