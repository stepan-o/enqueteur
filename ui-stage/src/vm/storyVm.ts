import type { StageEpisode, StageNarrativeBlock } from "../types/stage";

export interface EpisodeStoryViewModel {
  storyArc: unknown | null;
  longMemory: unknown | null;
  topLevelNarrative: StageNarrativeBlock[];
}

export function buildEpisodeStory(ep: StageEpisode): EpisodeStoryViewModel {
  const storyArc = ep && typeof ep.story_arc !== "undefined" ? ep.story_arc : null;
  const longMemory = ep && typeof ep.long_memory !== "undefined" ? ep.long_memory : null;
  const topLevelNarrative = Array.isArray(ep?.narrative) ? ep.narrative : [];
  return {
    storyArc: storyArc ?? null,
    longMemory: longMemory ?? null,
    topLevelNarrative,
  };
}
