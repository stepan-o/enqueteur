import styles from "./EpisodesIndexView.module.css";

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

  return (
    <div className={styles.root}>
      <h1 className={styles.header}>Episodes</h1>
      <p className={styles.explainer}>
        This is the episode index. For now, we show a stubbed list; later this
        will be wired to the backend source of truth.
      </p>

      <div className={styles.panel}>
        {items.length === 0 ? (
          <div className={styles.empty}>
            <p>No episodes available yet.</p>
            <p>
              You can still access the latest episode via the default view on
              the home route.
            </p>
          </div>
        ) : (
          <table className={styles.table} role="table" aria-label="Episodes list">
            <thead>
              <tr className={styles.tr}>
                <th className={styles.th} scope="col">Episode ID</th>
                <th className={styles.th} scope="col">Run ID</th>
                <th className={styles.th} scope="col">Index</th>
                <th className={styles.th} scope="col">Stage Version</th>
                <th className={styles.th} scope="col">Days</th>
                <th className={styles.th} scope="col">Summary</th>
                <th className={styles.th} scope="col">&nbsp;</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.id} className={styles.tr}>
                  <td className={`${styles.td} ${styles.id}`}>{truncateId(it.id)}</td>
                  <td className={`${styles.td} ${styles.runId}`}>{truncateId(it.runId)}</td>
                  <td className={styles.td}>{it.index}</td>
                  <td className={styles.td}>{it.stageVersion}</td>
                  <td className={styles.td}>{it.dayCount}</td>
                  <td className={styles.td}>{it.summary}</td>
                  <td className={styles.td}>
                    <button
                      type="button"
                      className={styles.viewBtn}
                      aria-disabled="true"
                      title="Coming soon"
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
