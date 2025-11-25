import type { EpisodeViewModel } from "../vm/episodeVm";
import { buildDayDetail } from "../vm/dayDetailVm";
import type { StageNarrativeBlock } from "../types/stage";
import { buildDaySummary } from "../vm/daySummaryVm";
import styles from "./DayDetailPanel.module.css";
import { tensionColor } from "../utils/tensionColors";

export interface DayDetailPanelProps {
  episode: EpisodeViewModel;
  dayIndex: number;
}

function formatNum(n: number, digits = 2): string {
  if (Number.isNaN(n) || !Number.isFinite(n)) return "0.00";
  return n.toFixed(digits);
}

function renderNarrativeItem(n: StageNarrativeBlock) {
  return (
    <li key={n.block_id ?? `${n.kind}-${n.text.slice(0, 12)}` } className={styles.narrativeItem}>
      <span className={styles.narrativeKind}>[{n.kind}]</span>
      <span>{n.text}</span>
    </li>
  );
}

export default function DayDetailPanel({ episode, dayIndex }: DayDetailPanelProps) {
  const detail = buildDayDetail(episode, dayIndex);
  const summary = buildDaySummary(episode, dayIndex);
  const isEmpty = detail.narrative.length === 0 && detail.agents.length === 0 && detail.tensionScore === 0 && detail.totalIncidents === 0 && detail.supervisorActivity === 0 && detail.perceptionMode === "unknown";

  if (isEmpty) {
    return (
      <div className={styles.panel} aria-live="polite">
        <div className={styles.header}>Day Detail</div>
        {/* Tension heat bar (empty state renders baseline) */}
        <div
          className={styles.tensionBar}
          data-testid="tension-bar"
          title={`Tension 0.00`}
        >
          <div
            className={styles.tensionFill}
            data-testid="tension-fill"
            style={{ width: `0%`, backgroundColor: tensionColor(0) }}
          />
        </div>
        <div className={styles.empty}>No data for day {dayIndex}.</div>
      </div>
    );
  }

  return (
    <section className={styles.panel} aria-label={`Day ${detail.index} detail`}>
      <div className={styles.header}>{`Day ${detail.index} — perception: ${detail.perceptionMode}`}</div>

      {/* Tension heat bar */}
      <div
        className={styles.tensionBar}
        data-testid="tension-bar"
        title={`Tension ${formatNum(detail.tensionScore)}`}
      >
        {(() => {
          const v = typeof detail.tensionScore === "number" && Number.isFinite(detail.tensionScore) ? Math.min(1, Math.max(0, detail.tensionScore)) : 0;
          const pct = `${Math.round(v * 100)}%`;
          const color = tensionColor(v);
          return (
            <div
              className={styles.tensionFill}
              data-testid="tension-fill"
              style={{ width: pct, backgroundColor: color }}
            />
          );
        })()}
      </div>

      <div className={styles.summary}>{summary.notableText}</div>

      <div className={styles.metaRow}>
        <span className={styles.metaItem}>Tension: {formatNum(detail.tensionScore)}</span>
        <span className={styles.metaItem}>Incidents: {detail.totalIncidents}</span>
        <span className={styles.metaItem}>Supervisor: {formatNum(detail.supervisorActivity)}</span>
      </div>

      <div className={styles.narrativeSection}>
        <div className={styles.header} style={{ fontWeight: 600, marginBottom: "0.25rem" }}>Narrative</div>
        {detail.narrative.length > 0 ? (
          <ul className={styles.narrativeList}>
            {detail.narrative.map(renderNarrativeItem)}
          </ul>
        ) : (
          <div className={styles.empty}>No narrative for this day.</div>
        )}
      </div>

      <div className={styles.agentsSection}>
        <div className={styles.header} style={{ fontWeight: 600, marginBottom: "0.25rem" }}>Agents</div>
        {detail.agents.length > 0 ? (
          <ul className={styles.agentsList}>
            {detail.agents.map((a) => (
              <li key={a.name} className={styles.agentRow}>
                <span className={styles.agentName}>{a.name}</span>
                <span className={styles.agentMeta}>
                  {a.role} • stress {formatNum(a.avgStress)} • guardrails {a.guardrailCount} • context {a.contextCount}
                  {a.attributionCause ? ` • cause ${a.attributionCause}` : ""}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <div className={styles.empty}>No agent activity recorded for this day.</div>
        )}
      </div>
    </section>
  );
}
