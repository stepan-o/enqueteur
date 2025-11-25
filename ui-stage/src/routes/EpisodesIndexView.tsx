import styles from "./EpisodesIndexView.module.css";
import { useEpisodeNavigator } from "../hooks/useEpisodeNavigator";

export interface EpisodeListItem {
  id: string;
  runId: string;
  index: number;
  stageVersion: number;
  dayCount: number;
  summary: string;
}

// Small, in-file mock builder. Keep self-contained and type-safe.
export function buildMockEpisodeList(): EpisodeListItem[] {
  return [
    {
      id: "ep-demo-1-abcdef012345",
      runId: "run-demo-1-xyz987654321",
      index: 0,
      stageVersion: 1,
      dayCount: 3,
      summary: "Decompression arc, 3 days, low incidents.",
    },
    {
      id: "ep-demo-2-fedcba987654",
      runId: "run-demo-2-abcd1234",
      index: 1,
      stageVersion: 1,
      dayCount: 4,
      summary: "Escalation phase, 4 days, moderate tension.",
    },
    {
      id: "ep-demo-3-1122334455",
      runId: "run-demo-3-5566778899",
      index: 2,
      stageVersion: 2,
      dayCount: 2,
      summary: "Short interlude, 2 days, quiet.",
    },
  ];
}

function truncateId(val: string): string {
  if (!val) return "";
  if (val.length <= 10) return val;
  return `${val.slice(0, 10)}…`;
}

export interface EpisodesIndexViewProps {
  items?: EpisodeListItem[];
}

export default function EpisodesIndexView({ items: propsItems }: EpisodesIndexViewProps) {
  const items = propsItems ?? buildMockEpisodeList();
  const { navigateToEpisode } = useEpisodeNavigator();

  return (
    <div className={styles.root}>
      <h1 className={styles.header}>Episodes</h1>
      <p className={styles.explainer}>
        This is the episode index. For now, we show a stubbed list; later this
        will be wired to the backend source of truth.
      </p>

      <section
        className={`${styles.panel} ${styles.section}`}
        aria-label="Episodes overview"
      >
        {items.length === 0 ? (
          <div className={styles.empty} aria-live="polite">
            <p>No episodes found.</p>
            <p>
              The latest episode is still accessible via the default view on the home route.
            </p>
          </div>
        ) : (
          <div>
            <div className={styles.headerRow} role="rowheader">
              <div className={styles.cell}>Episode ID</div>
              <div className={styles.cell}>Run ID</div>
              <div className={styles.cell}>Index</div>
              <div className={styles.cell}>Stage Version</div>
              <div className={styles.cell}>Days</div>
              <div className={styles.cell}>Summary</div>
              <div className={styles.cell}>&nbsp;</div>
            </div>
            <ul className={styles.list} aria-label="Episodes list">
              {items.map((it) => (
                <li key={it.id} className={styles.row} aria-label={`Episode row ${it.index}`}>
                  <div className={`${styles.cell} ${styles.id}`}>{truncateId(it.id)}</div>
                  <div className={`${styles.cell} ${styles.runId}`}>{truncateId(it.runId)}</div>
                  <div className={styles.cell}>{it.index}</div>
                  <div className={styles.cell}>{it.stageVersion}</div>
                  <div className={styles.cell}>{it.dayCount}</div>
                  <div className={styles.cell}>{it.summary}</div>
                  <div className={styles.cell}>
                    <button
                      type="button"
                      className={styles.viewBtn}
                      onClick={() => navigateToEpisode(it.id)}
                      aria-label={`View Episode ${it.id}`}
                    >
                      View Episode
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}
