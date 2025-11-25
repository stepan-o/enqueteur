import type { EpisodeStoryViewModel } from "../vm/storyVm";
import type { StageNarrativeBlock } from "../types/stage";
import styles from "./EpisodeStoryPanel.module.css";
import NarrativeBlockV2 from "./NarrativeBlockV2";

export interface EpisodeStoryPanelProps {
  story: EpisodeStoryViewModel;
}

function renderBlock(b: StageNarrativeBlock) {
  return (
    <NarrativeBlockV2
      key={b.block_id ?? `${b.kind}-${b.text.slice(0, 12)}`}
      block={b}
      dedupeKindTag
    />
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
          {/* Minimal structured render if common fields exist */}
          {(() => {
            const arc: any = story.storyArc;
            const hasSummary = arc && typeof arc.summary === "string" && arc.summary.length > 0;
            const hasBeats = arc && Array.isArray(arc.beats) && arc.beats.length > 0;
            return (
              <div>
                {hasSummary ? (
                  <div>
                    <div className={styles.subSectionTitle}>arc summary</div>
                    <div>{arc.summary}</div>
                  </div>
                ) : null}
                {hasBeats ? (
                  <div>
                    <div className={styles.subSectionTitle}>beats</div>
                    <div>
                      {(arc.beats as any[]).map((b, i) => (
                        <div key={`beat-${i}`} className={styles.block}>
                          {typeof b === "string" ? b : JSON.stringify(b)}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
                {!hasSummary && !hasBeats ? (
                  <div className={styles.muted}>No arc fields available.</div>
                ) : null}
              </div>
            );
          })()}
          {/* Preserve raw JSON for full visibility */}
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
