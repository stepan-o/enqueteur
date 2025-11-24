import type { AgentViewModel } from "../vm/agentVm";
import styles from "./EpisodeAgentsOverview.module.css";

export interface EpisodeAgentsOverviewProps {
  agents: AgentViewModel[];
}

function formatNum(n: number | null | undefined, digits = 2): string {
  const v = typeof n === "number" ? n : 0;
  if (!Number.isFinite(v)) return "0.00";
  return v.toFixed(digits);
}

export default function EpisodeAgentsOverview({
  agents,
}: EpisodeAgentsOverviewProps) {
  const list = [...(agents || [])].sort((a, b) => a.name.localeCompare(b.name));

  if (list.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.empty}>No agents recorded for this episode.</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <ul className={styles.list}>
        {list.map((a) => (
          <li key={a.name} className={styles.item}>
            <div>
              <span className={styles.name}>{a.name}</span>
              <span className={styles.role}>— role {a.role}</span>
            </div>
            <div className={styles.meta}>
              Stress Δ: {formatNum(a.stressDelta)} (start {formatNum(a.stressStart)} → end {formatNum(a.stressEnd)})
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
