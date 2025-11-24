import type { EpisodeViewModel } from "../vm/episodeVm";
import type { StageEpisode, StageDay } from "../types/stage";
import styles from "./EpisodeAgentsPanel.module.css";

export interface EpisodeAgentsPanelProps {
  episode: EpisodeViewModel;
}

function formatNum(n: number | null | undefined, digits = 2): string {
  const v = typeof n === "number" ? n : 0;
  if (!Number.isFinite(v)) return "0.00";
  return v.toFixed(digits);
}

function computeAvgStress(raw: StageEpisode, agentName: string): number {
  const days: StageDay[] = Array.isArray(raw.days) ? raw.days : [];
  let sum = 0;
  let count = 0;
  for (const d of days) {
    const map = d.agents || {};
    const a = map[agentName as keyof typeof map];
    if (a) {
      const v = a.avg_stress;
      const num = Number.isFinite(v) ? v : 0;
      sum += num;
      count += 1;
    }
  }
  if (count === 0) return 0;
  return sum / count;
}

function latestAttribution(raw: StageEpisode, agentName: string): string | null {
  const days: StageDay[] = Array.isArray(raw.days) ? raw.days : [];
  // Iterate in ascending order, keep the last non-null seen
  let last: string | null = null;
  for (const d of days) {
    const map = d.agents || {};
    const a = map[agentName as keyof typeof map];
    const cause = a && typeof a.attribution_cause === "string" ? a.attribution_cause : null;
    if (cause) last = cause;
  }
  return last;
}

export default function EpisodeAgentsPanel({ episode }: EpisodeAgentsPanelProps) {
  const raw = episode?._raw as StageEpisode | undefined;
  const agentsMap = raw?.agents || {};
  const names = Object.keys(agentsMap);

  if (names.length === 0) {
    return (
      <section className={styles.panel} aria-label="Episode agents">
        <div className={styles.empty}>No agents recorded for this episode.</div>
      </section>
    );
  }

  const items = names
    .map((name) => {
      const s = agentsMap[name as keyof typeof agentsMap] as (typeof agentsMap)[string] | undefined;
      const role: string = s?.role ?? "";
      const guardrail: number = typeof s?.guardrail_total === "number" ? s.guardrail_total : 0;
      const context: number = typeof s?.context_total === "number" ? s.context_total : 0;
      const avg = raw ? computeAvgStress(raw, name) : 0;
      const cause = raw ? latestAttribution(raw, name) : null;
      return { name, role, guardrail, context, avg, cause };
    })
    .sort((a, b) => a.name.localeCompare(b.name));

  return (
    <section className={styles.panel} aria-label="Episode agents">
      <ul className={styles.list}>
        {items.map((a) => (
          <li key={a.name} className={styles.row}>
            <div>
              <span className={styles.name}>{a.name}</span>
              <span className={styles.role}>— {a.role}</span>
            </div>
            <div className={styles.meta}>
              avg stress {formatNum(a.avg)} • guardrails {a.guardrail} • context {a.context}
              {a.cause ? ` • cause ${a.cause}` : ""}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
