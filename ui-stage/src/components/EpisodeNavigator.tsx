import styles from "./EpisodeNavigator.module.css";

export interface EpisodeNavigatorProps {
  currentEpisodeId: string | null;
  currentEpisodeIndex: number;
}

function truncate(val: string): string {
  if (!val) return "";
  // Simple truncation: first 6 chars + … if length > 10
  return val.length > 10 ? `${val.slice(0, 6)}…` : val;
}

export default function EpisodeNavigator({
  currentEpisodeId,
  currentEpisodeIndex,
}: EpisodeNavigatorProps) {
  return (
    <section
      className={styles.panel}
      aria-label="Episode navigator"
      data-testid="episode-navigator"
    >
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h2 className={styles.title}>Episode Navigator</h2>
          <span className={styles.badge}>stub</span>
        </div>
        <p className={styles.subTitle}>
          This is a non-interactive preview. Navigation will be wired in a later era.
        </p>
      </header>

      <div className={styles.currentBlock} data-testid="episode-nav-current">
        <div className={styles.currentLabel}>Current episode</div>
        <div className={styles.currentIdRow}>
          <span className={styles.currentIndex}>{`#${currentEpisodeIndex}`}</span>
          {currentEpisodeId && (
            <span className={styles.currentId} title={currentEpisodeId}>
              {truncate(currentEpisodeId)}
            </span>
          )}
        </div>
      </div>

      <div className={styles.miniMap} aria-label="Episode mini-map overview">
        <div className={styles.dotRow}>
          <span className={styles.dot} data-testid="episode-nav-dot-prev" />
          <span
            className={`${styles.dot} ${styles.dotCurrent}`}
            data-testid="episode-nav-dot-current"
          />
          <span className={styles.dot} data-testid="episode-nav-dot-next" />
        </div>
        <div className={styles.caption}>Previous • Current • Next (preview only)</div>
      </div>
    </section>
  );
}

export { truncate };
