import type { EpisodeViewModel } from "./episodeVm";
import { buildDayDetail } from "./dayDetailVm";

export interface DayStoryboardItemViewModel {
  dayIndex: number; // 0-based
  label: string; // e.g., "Day 0"
  caption: string; // short narrative snippet or fallback
  tensionScore: number | null;
  hasIncidents: boolean;
  supervisorActivity: number | null;
}

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
      return {
        dayIndex: d.index,
        label: `Day ${d.index}`,
        caption,
        tensionScore: isFiniteNumber(d.tensionScore) ? d.tensionScore : null,
        hasIncidents: (typeof d.totalIncidents === "number" ? d.totalIncidents : 0) > 0,
        supervisorActivity: isFiniteNumber(d.supervisorActivity)
          ? d.supervisorActivity
          : null,
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
    if (b && typeof b.text === "string" && b.text.trim().length > 0) {
      return b.text.trim();
    }
  }
  return null;
}

function isFiniteNumber(n: unknown): n is number {
  return typeof n === "number" && Number.isFinite(n);
}
