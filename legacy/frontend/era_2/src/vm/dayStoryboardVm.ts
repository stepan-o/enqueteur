import type { EpisodeViewModel } from "./episodeVm";
import { buildDayDetail } from "./dayDetailVm";
import type { AgentViewModel } from "./agentVm";
import { buildAgentViews } from "./agentVm";

export interface DayStoryboardItemViewModel {
  dayIndex: number; // 0-based
  label: string; // e.g., "Day 0"
  caption: string; // short narrative snippet or fallback
  tensionScore: number | null;
  hasIncidents: boolean;
  supervisorActivity: number | null;
  /** Narrative lane items for this day (minimal, ordered as in raw). */
  narrativeLane: StoryboardItem[];
  /** Optional tiny agent cameos for this day (Phase 3C). */
  agentCameos?: DayAgentCameo[];
  /** If more than shown cameos exist, render "+N" overflow indicator. */
  agentCameoOverflowCount?: number;
  /**
   * Tiny per-day tension trend normalized to [0,1].
   * If underlying data is missing or degenerate (flat/NaN), this is [].
   */
  sparklinePoints?: number[];
  /**
   * Subtle background band classification. Based on day-level average tension (tensionScore).
   * Thresholds:
   *  avg < 0.25 → tensionLow
   *  avg < 0.55 → tensionMedium
   *  else       → tensionHigh
   */
  tensionBandClass?: "tensionLow" | "tensionMedium" | "tensionHigh";
}

export type DayAgentCameo = {
  name: string;
  roleLabel: string;
  vibeColorKey: NonNullable<AgentViewModel["vibeColorKey"]> | "neutral";
  /** Simplified stress tier for cameo badges */
  stressTier: "low" | "mid" | "high";
  hasAttribution: boolean;
};

export type StoryboardItem = {
  lane: "narrative";
  dayIndex: number;
  blockId: string;
  kind: string;
  text: string;
  tags: string[];
};

/**
 * Build storyboard items from an EpisodeViewModel using only existing data.
 * Defensive: if episode or arrays are malformed, return an empty list.
 */
export function buildDayStoryboardItems(
  episode: EpisodeViewModel | null | undefined
): DayStoryboardItemViewModel[] {
  try {
    if (!episode || !Array.isArray((episode as any).days)) return [];
    // Precompute agent identity map from raw for vibeColorKey and stressTier reuse
    let agentIdentities: Record<string, AgentViewModel> = {};
    try {
      const raw = (episode as any)?._raw;
      if (raw && raw.agents) {
        const views = buildAgentViews(raw);
        agentIdentities = Object.fromEntries(views.map((a) => [a.name, a]));
      }
    } catch {
      agentIdentities = {};
    }
    const items: DayStoryboardItemViewModel[] = episode.days.map((d) => {
      const detail = safeBuildDetail(episode, d.index);
      const caption = firstNarrativeText(detail?.narrative) ?? "No major events logged.";
      const narrativeLane = buildNarrativeLane(episode, d.index);
      const { cameos: agentCameos, overflow } = buildAgentCameos(episode, d.index, agentIdentities);
      const spark = buildSparklinePoints(episode, d.index, d.tensionScore);
      const band = classifyBand(isFiniteNumber(d.tensionScore) ? d.tensionScore : 0);
      return {
        dayIndex: d.index,
        label: `Day ${d.index}`,
        caption,
        tensionScore: isFiniteNumber(d.tensionScore) ? d.tensionScore : null,
        hasIncidents: (d.totalIncidents) > 0,
        supervisorActivity: isFiniteNumber(d.supervisorActivity)
          ? d.supervisorActivity
          : null,
        narrativeLane,
        agentCameos,
        agentCameoOverflowCount: overflow,
        sparklinePoints: spark,
        tensionBandClass: band,
      };
    });
    // Ensure stable ordering by day index (defensive)
    items.sort((a, b) => a.dayIndex - b.dayIndex);
    return items;
  } catch {
    return [];
  }
}

function buildAgentCameos(
  episode: EpisodeViewModel,
  dayIndex: number,
  identities: Record<string, AgentViewModel>
): { cameos: DayAgentCameo[]; overflow: number } {
  try {
    const raw: any = (episode as any)?._raw;
    const days = Array.isArray(raw?.days) ? raw.days : [];
    const rawDay = days.find((d: any) => d && d.day_index === dayIndex);
    const agentMap = (rawDay && typeof rawDay.agents === "object" && rawDay.agents) || {};
    const entries = Object.entries(agentMap) as Array<[string, any]>;
    if (entries.length === 0) return { cameos: [], overflow: 0 };

    // Deterministic sort: by avg_stress desc, then name asc
    entries.sort((a, b) => {
      const av = Number.isFinite(a[1]?.avg_stress) ? a[1].avg_stress : -1;
      const bv = Number.isFinite(b[1]?.avg_stress) ? b[1].avg_stress : -1;
      if (bv !== av) return bv - av;
      return a[0].localeCompare(b[0]);
    });

    const maxShown = 3;
    const shown = entries.slice(0, maxShown);
    const overflow = Math.max(0, entries.length - shown.length);

    const mapTier = (t: AgentViewModel["stressTier"] | undefined): "low" | "mid" | "high" => {
      if (t === "high") return "high";
      if (t === "medium" || t === "cooldown") return "mid";
      return "low";
    };

    const cameos: DayAgentCameo[] = shown.map(([name, a]) => {
      const ident = identities[name] || identities[a?.name] || ({} as AgentViewModel);
      const roleLabel = (a?.role || ident?.role || "").toString();
      const vibe = (ident?.vibeColorKey as any) || "neutral";
      const tier = mapTier(ident?.stressTier);
      const hasAttr = typeof a?.attribution_cause === "string" && a.attribution_cause.trim().length > 0;
      return {
        name: a?.name || name,
        roleLabel,
        vibeColorKey: vibe,
        stressTier: tier,
        hasAttribution: hasAttr,
      };
    });
    return { cameos, overflow };
  } catch {
    return { cameos: [], overflow: 0 };
  }
}

function safeBuildDetail(ep: EpisodeViewModel, dayIndex: number) {
  try {
    return buildDayDetail(ep, dayIndex);
  } catch {
    return null as any;
  }
}

function firstNarrativeText(
  narrative: Array<{ text?: unknown }> | undefined | null
): string | null {
  if (!Array.isArray(narrative)) return null;
  for (const b of narrative) {
    const text = b && typeof (b as any).text === "string" ? ((b as any).text as string) : null;
    if (text && text.trim().length > 0) {
      return text.trim();
    }
  }
  return null;
}

function isFiniteNumber(n: unknown): n is number {
  return typeof n === "number" && Number.isFinite(n);
}

function buildNarrativeLane(
  episode: EpisodeViewModel,
  dayIndex: number
): StoryboardItem[] {
  try {
    const raw: any = (episode as any)?._raw;
    const days = Array.isArray(raw?.days) ? raw.days : [];
    const rawDay = days.find((d: any) => d && d.day_index === dayIndex);
    const blocks = Array.isArray(rawDay?.narrative) ? rawDay.narrative : [];
    const items: StoryboardItem[] = [];
    for (const b of blocks) {
      if (!b || typeof b !== "object") continue;
      const blockId = typeof b.block_id === "string" && b.block_id ? b.block_id : null;
      const kind = typeof b.kind === "string" ? b.kind : null;
      const text = typeof b.text === "string" ? b.text : null;
      const tags = Array.isArray(b.tags) ? (b.tags as unknown[]) : [];
      const tagStrings: string[] = tags.filter((t) => typeof t === "string") as string[];
      if (!blockId || !kind || !text) continue; // drop malformed entries
      items.push({
        lane: "narrative",
        dayIndex,
        blockId,
        kind,
        text,
        tags: tagStrings,
      });
    }
    // preserve given order
    return items;
  } catch {
    return [];
  }
}

/**
 * Build a tiny per-day sparkline from available data.
 * Prefers a pair [prevDayTension, currentDayTension] from episode.days.
 * If only one value is available or values are equal/invalid, returns [].
 */
function buildSparklinePoints(
  episode: EpisodeViewModel,
  dayIndex: number,
  tensionScore: number | undefined | null
): number[] {
  try {
    const days = Array.isArray((episode as any).days) ? (episode as any).days : [];
    const current = isFiniteNumber(tensionScore) ? tensionScore! : null;
    const prevDay = days.find((d: any) => d && d.index === dayIndex - 1);
    const prev = isFiniteNumber(prevDay?.tensionScore) ? (prevDay!.tensionScore as number) : null;

    const points: number[] = [];
    if (prev !== null && current !== null) {
      points.push(prev, current);
    } else if (current !== null) {
      // Not enough to draw a line; treat as degenerate
      return [];
    }
    if (points.length < 2) return [];

    // Normalize to [0,1]; if flat (min==max) treat as degenerate → []
    const min = Math.min(...points);
    const max = Math.max(...points);
    if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) return [];
    return points.map((v) => (v - min) / (max - min));
  } catch {
    return [];
  }
}

function classifyBand(avg: number): "tensionLow" | "tensionMedium" | "tensionHigh" {
  const v = Number.isFinite(avg) ? Math.max(0, Math.min(1, avg)) : 0;
  if (v < 0.25) return "tensionLow";
  if (v < 0.55) return "tensionMedium";
  return "tensionHigh";
}
