import type { EpisodeViewModel } from "../vm/episodeVm";
import { buildDayDetail } from "../vm/dayDetailVm";
import { buildDaySummary } from "../vm/daySummaryVm";
import styles from "./DayDetailPanel.module.css";
import { tensionColor } from "../utils/tensionColors";
import { stressColor } from "../utils/stressColor";
import NarrativeBlockV2 from "./NarrativeBlockV2";
import AgentAvatar from "./AgentAvatar";

export interface DayDetailPanelProps {
  episode: EpisodeViewModel;
  dayIndex: number;
}

function formatNum(n: number, digits = 2): string {
  if (Number.isNaN(n) || !Number.isFinite(n)) return "0.00";
  return n.toFixed(digits);
}

// replaced by NarrativeBlock component for readability and expressiveness

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
          const v = Number.isFinite(detail.tensionScore) ? Math.min(1, Math.max(0, detail.tensionScore)) : 0;
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

      <section className={styles.narrativeSection} aria-label="Day narrative">
        <div className={styles.header} style={{ fontWeight: 600, marginBottom: "0.25rem" }}>Narrative</div>
        {detail.narrative.length > 0 ? (
          <div>
            {detail.narrative.map((b) => (
              <NarrativeBlockV2 key={b.block_id ?? `${b.kind}-${b.text.slice(0, 12)}`} block={b} />
            ))}
          </div>
        ) : (
          <div className={styles.empty}>No narrative for this day.</div>
        )}
      </section>

      <div className={styles.agentsSection}>
        <div className={styles.header} style={{ fontWeight: 600, marginBottom: "0.25rem" }}>Agents</div>
        {detail.agents.length > 0 ? (
          <ul className={styles.agentsList}>
            {detail.agents.map((a) => (
              <li key={a.name} className={styles.agentRow}>
                <div className={styles.agentLeft}>
                  <span className={styles.avatar} aria-label={`Avatar for ${a.name}`}>
                    {/* Render AgentAvatar v2; keep wrapper aria-label for legacy tests */}
                    <AgentAvatar
                      name={a.name}
                      vibeColorKey={"neutral"}
                      stressTier={"none"}
                      size="md"
                    />
                  </span>
                  <div>
                    <span className={styles.agentName}>{a.name}</span>
                    <span className={styles.agentMeta}>— {a.role}</span>
                    <span
                      className={styles.stressDot}
                      title={`Stress ${formatNum(a.avgStress)}`}
                      style={{ backgroundColor: stressColor(a.avgStress ?? 0) }}
                      data-testid={`day-agent-stress-dot-${a.name}`}
                    />
                  </div>
                </div>
                <div className={styles.agentMeta}>
                  <span className={styles.badges}>
                    <span className={styles.badge} title="Guardrails" data-testid={`day-badge-g-${a.name}`}>G: {a.guardrailCount}</span>
                    <span className={styles.badge} title="Context" data-testid={`day-badge-c-${a.name}`}>C: {a.contextCount}</span>
                  </span>
                  {a.attributionCause ? ` • cause ${a.attributionCause}` : ""}
                </div>
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

function getAvatarSymbol(name: string): string {
  const ch = (name || "?").trim().charAt(0);
  return ch ? ch.toUpperCase() : "?";
}

function getAgentVibe(episode: EpisodeViewModel, name: string): string {
  const raw: any = (episode as any)?._raw;
  const summary = raw?.agents?.[name];
  const v = typeof summary?.vibe === "string" ? summary.vibe : "neutral";
  return v;
}

function getAgentVisual(episode: EpisodeViewModel, name: string): string {
  const raw: any = (episode as any)?._raw;
  const summary = raw?.agents?.[name];
  const v = typeof summary?.visual === "string" ? summary.visual : name;
  return v;
}
