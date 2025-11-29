import type { StageEpisode, StageNarrativeBlock } from "../types/stage";

export interface EpisodeStoryViewModel {
  storyArc: any | null;
  longMemory: any | null;
  topLevelNarrative: StageNarrativeBlock[];
}

/**
 * Build a UI-safe story view from a raw StageEpisode.
 * Normalizes optional fields and guards against malformed shapes.
 */
export function buildStoryView(raw: StageEpisode): EpisodeStoryViewModel {
  const arc = (raw as any)?.story_arc;
  const mem = (raw as any)?.long_memory;

  const storyArc = arc && typeof arc === "object" && !Array.isArray(arc) ? arc : null;
  const longMemory = mem && typeof mem === "object" && !Array.isArray(mem) ? mem : null;

  const topLevelRaw = (raw as any)?.narrative;
  let topLevelNarrative: StageNarrativeBlock[] = [];
  if (Array.isArray(topLevelRaw)) {
    const allValid = topLevelRaw.every(
      (b: any) => b && typeof b.kind === "string" && typeof b.text === "string"
    );
    if (allValid) {
      // Preserve original reference when possible (useful for tests/snapshots)
      topLevelNarrative = topLevelRaw as StageNarrativeBlock[];
    } else {
      topLevelNarrative = topLevelRaw.filter(
        (b: any) => b && typeof b.kind === "string" && typeof b.text === "string"
      ) as StageNarrativeBlock[];
    }
  }

  return { storyArc, longMemory, topLevelNarrative };
}

// Backward-compatibility: older code/tests may import buildEpisodeStory
export function buildEpisodeStory(ep: StageEpisode): EpisodeStoryViewModel {
  return buildStoryView(ep);
}
