import type { EpisodeViewModel } from "./episodeVm";

/**
 * EpisodeArcMood (v0.5)
 *
 * Intent: classify the episode-wide arc based on the global delta across the full
 * tensionTrend array (max minus min), not the day-to-day direction between adjacent
 * points. This complements DayDetail/TimelineStrip, which focus on local daily
 * direction. Keep exports stable; this is documentation + clarity only.
 */

export interface EpisodeArcMoodViewModel {
  label: string;        // human label for episode-wide arc mood
  icon: string;         // emoji icon: 🌿, 🔶, 🔺, ⚡
  tensionClass: "calm" | "minor" | "medium" | "spike"; // public enum unchanged
  summaryLine: string;  // one-line capsule
  /** Optional, additive: expose direction for UI styling. "mixed" when spiky. */
  direction?: Direction | "mixed";
}

function classifyDelta(delta: number): "calm" | "minor" | "medium" | "spike" {
  // Episode-wide arc classification thresholds based on global delta (max-min).
  // Note: This does not consider daily direction; it operates on the full span.
  // Last bucket is interpreted as >= 0.45 → spike.
  if (delta < 0.1) return "calm";
  if (delta < 0.25) return "minor";
  if (delta < 0.45) return "medium";
  return "spike";
}

type Direction = "up" | "down" | "flat";

const EPS = 0.05; // ignore micro-noise for direction and sign changes

function computeSlope(values: number[]): number {
  if (values.length < 2) return 0;
  return values[values.length - 1] - values[0];
}

function classifyDirection(slope: number): Direction {
  if (Math.abs(slope) < EPS) return "flat";
  return slope > 0 ? "up" : "down";
}

function countSignChanges(values: number[]): number {
  if (values.length < 3) return 0;
  let changes = 0;
  let prevSign = 0; // -1, 0, +1
  for (let i = 1; i < values.length; i++) {
    const diff = values[i] - values[i - 1];
    const sign = Math.abs(diff) < EPS ? 0 : diff > 0 ? 1 : -1;
    if (sign === 0) continue;
    if (prevSign !== 0 && sign !== prevSign) changes++;
    prevSign = sign;
  }
  return changes;
}

function labelFor(
  cls: EpisodeArcMoodViewModel["tensionClass"],
  direction: Direction,
  mixed: boolean
): string {
  // Icons remain mapped by cls; label reflects direction + shape awareness
  if (cls === "calm") {
    return "Steady State";
  }
  if (mixed) {
    if (cls === "spike") return "Volatile Arc";
    return "Uneven Tension"; // covers minor/medium mixed
  }
  if (direction === "up") {
    if (cls === "minor") return "Minor Escalation";
    if (cls === "medium") return "Building Pressure";
    return "Critical Spike"; // spike + up
  }
  if (direction === "down") {
    if (cls === "minor") return "Gentle Release";
    if (cls === "medium") return "Softening Arc";
    return "Rapid Unwind"; // spike + down
  }
  // flat but not calm (some movement without clear direction)
  return "Uneven Tension";
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

// Direction-aware icon mapping (internal). Keeps public type stable.
function iconForWithDirection(
  cls: EpisodeArcMoodViewModel["tensionClass"],
  direction: Direction,
  mixed: boolean
): string {
  if (cls === "calm") return "🌿"; // steady regardless of direction
  if (cls === "spike") return "⚡"; // spike: glyph remains ⚡ regardless of direction/mixed
  if (mixed) return "🌀"; // signal wobble/instability for minor/medium
  if (cls === "minor") {
    if (direction === "down") return "🔽";
    // flat or up → maintain gentle diamond for subtle movement
    return "🔶";
  }
  if (cls === "medium") {
    if (direction === "down") return "🔻";
    // flat or up → up-triangle
    return "🔺";
  }
  return "🔶"; // fallback shouldn't happen; keep safe glyph
}

export function buildEpisodeArcMood(episode: EpisodeViewModel): EpisodeArcMoodViewModel {
  // Use the full tensionTrend span and measure global delta. This is an
  // episode-wide arc heuristic; daily up/down is handled elsewhere.
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
  const slope = computeSlope(values);
  const direction = classifyDirection(slope);
  const signChanges = countSignChanges(values);
  const mixed = signChanges >= 2 && cls !== "calm"; // consider 2+ direction flips as mixed
  const label = labelFor(cls, direction, mixed);
  const icon = iconForWithDirection(cls, direction, mixed);

  // Summary: first top-level narrative block text if present, else fallback.
  // The intent is to provide a short human line to accompany the episode arc.
  const firstText = (episode?.story?.topLevelNarrative && episode.story.topLevelNarrative[0]?.text) || "";
  let summaryLine: string;
  if (firstText.length > 0) {
    summaryLine = firstText;
  } else if (cls === "calm" || direction === "flat") {
    summaryLine = "Behavior remains relatively steady.";
  } else if (mixed) {
    summaryLine = "Tension fluctuates with no clear direction.";
  } else if (direction === "up") {
    summaryLine = "Tension builds across the episode.";
  } else {
    summaryLine = "Tension eases off over the episode.";
  }

  return { label, icon, tensionClass: cls, summaryLine, direction: mixed ? "mixed" : direction };
}
