import type { EpisodeViewModel } from "./episodeVm";
import { buildDayDetail } from "./dayDetailVm";

export interface DayStoryboardItemViewModel {
  dayIndex: number; // 0-based
  label: string; // e.g., "Day 0"
  caption: string; // short narrative snippet or fallback
  tensionScore: number | null;
  hasIncidents: boolean;
  supervisorActivity: number | null;
  /** Narrative lane items for this day (minimal, ordered as in raw). */
  narrativeLane: StoryboardItem[];
}

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
    const items: DayStoryboardItemViewModel[] = episode.days.map((d) => {
      const detail = safeBuildDetail(episode, d.index);
      const caption = firstNarrativeText(detail?.narrative) ?? "No major events logged.";
      const narrativeLane = buildNarrativeLane(episode, d.index);
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
      };
    });
    // Ensure stable ordering by day index (defensive)
    items.sort((a, b) => a.dayIndex - b.dayIndex);
    return items;
  } catch {
    return [];
  }
}

function safeBuildDetail(ep: EpisodeViewModel, dayIndex: number) {
  try {
    return buildDayDetail(ep, dayIndex);
  } catch {
    return null as any;
  }
}

function firstNarrativeText(narrative: { text: string }[] | undefined | null): string | null {
  if (!Array.isArray(narrative)) return null;
  for (const b of narrative) {
    if (b && b.text.trim().length > 0) {
      return b.text.trim();
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
