import type { EpisodeViewModel } from "../vm/episodeVm";
import styles from "./EpisodeHeader.module.css";

export interface EpisodeHeaderProps {
  episode: EpisodeViewModel;
}

export default function EpisodeHeader({ episode }: EpisodeHeaderProps) {
  const dayCount = episode.days.length;
  return (
    <header className={styles.header} aria-label="Episode header">
      <div className={styles.row}>
        <span className={styles.item}>
          <span className={styles.icon} aria-hidden>◉</span>
          <span className={styles.label}>Episode:</span> {episode.id ?? "—"}
        </span>
        <span className={styles.sep} aria-hidden>
          •
        </span>
        <span className={styles.item}>
          <span className={styles.icon} aria-hidden>↳</span>
          <span className={styles.label}>Run:</span> {episode.runId ?? "—"}
        </span>
        <span className={styles.sep} aria-hidden>
          •
        </span>
        <span className={styles.item}>
          <span className={styles.icon} aria-hidden>⚙</span>
          <span className={styles.label}>Stage Version:</span> {episode.stageVersion}
        </span>
        <span className={styles.sep} aria-hidden>
          •
        </span>
        <span className={styles.item}>
          <span className={styles.icon} aria-hidden>∙</span>
          <span className={styles.label}>Days:</span> {dayCount}
        </span>
      </div>
    </header>
  );
}
