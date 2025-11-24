import type { EpisodeStoryViewModel } from "../vm/storyVm";
import type { StageNarrativeBlock } from "../types/stage";
import styles from "./EpisodeStoryPanel.module.css";

export interface EpisodeStoryPanelProps {
  story: EpisodeStoryViewModel;
}

function renderBlock(b: StageNarrativeBlock) {
  return (
    <div key={b.block_id ?? `${b.kind}-${b.text.slice(0, 12)}`} className={styles.block}>
      <strong>{b.kind}</strong>: {b.text}
    </div>
  );
}

export default function EpisodeStoryPanel({ story }: EpisodeStoryPanelProps) {
  const hasStoryArc = story && story.storyArc != null;
  const hasLongMemory = story && story.longMemory != null;
  const hasNarrative = Array.isArray(story?.topLevelNarrative) && story.topLevelNarrative.length > 0;

  const isEmpty = !hasStoryArc && !hasLongMemory && !hasNarrative;

  if (isEmpty) {
    return (
      <section className={styles.panel} aria-label="Episode story">
        <div className={styles.empty}>No story arc or long-memory data for this episode.</div>
      </section>
    );
  }

  return (
    <section className={styles.panel} aria-label="Episode story">
      {hasStoryArc && (
        <div>
          <h3 className={styles.sectionTitle}>Story Arc</h3>
          <pre>{JSON.stringify(story.storyArc, null, 2)}</pre>
        </div>
      )}

      {hasLongMemory && (
        <div>
          <h3 className={styles.sectionTitle}>Long Memory</h3>
          <pre>{JSON.stringify(story.longMemory, null, 2)}</pre>
        </div>
      )}

      {hasNarrative && (
        <div>
          <h3 className={styles.sectionTitle}>Top-Level Narrative</h3>
          <div className={styles.blocks}>
            {story.topLevelNarrative.map(renderBlock)}
          </div>
        </div>
      )}
    </section>
  );
}
