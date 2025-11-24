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
          <strong>Episode:</strong> {episode.id ?? "—"}
        </span>
        <span className={styles.sep} aria-hidden>
          •
        </span>
        <span className={styles.item}>
          <strong>Run:</strong> {episode.runId ?? "—"}
        </span>
        <span className={styles.sep} aria-hidden>
          •
        </span>
        <span className={styles.item}>
          <strong>Stage Version:</strong> {episode.stageVersion}
        </span>
        <span className={styles.sep} aria-hidden>
          •
        </span>
        <span className={styles.item}>
          <strong>Days:</strong> {dayCount}
        </span>
      </div>
    </header>
  );
}
