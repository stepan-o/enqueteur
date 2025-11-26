import type { EpisodeViewModel } from "../vm/episodeVm";
import type { StageEpisode, StageDay } from "../types/stage";
import styles from "./EpisodeAgentsPanel.module.css";
import { stressColor } from "../utils/stressColor";
import AgentAvatar from "./AgentAvatar";
import { buildPanelAgents } from "../vm/agentVm";

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

// Avatar visuals handled by AgentAvatarV1

function buildSparklinePoints(raw: StageEpisode, agentName: string, width = 60, height = 18): string {
  const days: StageDay[] = Array.isArray(raw.days) ? raw.days : [];
  const values: number[] = days
    .map((d) => d.agents?.[agentName as keyof typeof d.agents])
    .map((a: any) => (a && Number.isFinite(a.avg_stress) ? (a.avg_stress as number) : 0)) as number[];
  const pts = values.length === 1 ? [values[0], values[0]] : values;
  const n = pts.length;
  if (n === 0) return "";
  const step = n > 1 ? width / (n - 1) : 0;
  const toY = (v: number) => {
    const clamped = Math.max(0, Math.min(1, v || 0));
    return (1 - clamped) * height;
  };
  const coords: string[] = [];
  for (let i = 0; i < n; i++) {
    const x = i * step;
    const y = toY(pts[i]);
    coords.push(`${x.toFixed(1)},${y.toFixed(1)}`);
  }
  return coords.join(" ");
}

export default function EpisodeAgentsPanel({ episode }: EpisodeAgentsPanelProps) {
  const raw = episode?._raw as StageEpisode | undefined;
  const panelAgents = buildPanelAgents(episode);

  if (panelAgents.length === 0) {
    return (
      <section className={styles.panel} aria-label="Episode agents">
        <div className={styles.empty}>No agents recorded for this episode.</div>
      </section>
    );
  }

  const items = panelAgents.map((a) => {
    const avg = a.avgStress ?? (raw ? computeAvgStress(raw, a.name) : 0);
    const cause = a.latestAttributionCause ?? (raw ? latestAttribution(raw, a.name) : null);
    const stress = stressColor(avg);
    const spark = a.sparkPoints ?? (raw ? buildSparklinePoints(raw, a.name) : "");
    return {
      name: a.name,
      role: a.role || "",
      guardrail: a.guardrailTotal ?? 0,
      context: a.contextTotal ?? 0,
      avg,
      cause,
      stress,
      spark,
      vibeColorKey: a.vibeColorKey,
      stressTier: a.stressTier,
      displayTagline: a.displayTagline,
      tagline: a.tagline,
    };
  });

  return (
    <section className={styles.panel} aria-label="Episode agents">
      <ul className={styles.list}>
        {items.map((a) => (
          <li key={a.name} className={styles.row}>
            <div className={styles.left}>
              <span className={styles.avatarSlot} aria-label={`Avatar for ${a.name}`}>
                <AgentAvatar name={a.name} vibeColorKey={a.vibeColorKey} stressTier={a.stressTier} size="md" />
              </span>
              <div>
                <div className={styles.titleRow}>
                  <span className={styles.name}>{a.name}</span>
                  <span className={styles.role}>— {a.role}</span>
                  <span
                    className={styles.stressDot}
                    title={`Stress ${formatNum(a.avg)}`}
                    style={{ backgroundColor: a.stress }}
                    data-testid={`agent-stress-dot-${a.name}`}
                  />
                </div>
                <div className={styles.tagline}>{a.displayTagline || a.tagline || "System agent"}</div>
                <svg
                  className={styles.sparkline}
                  role="img"
                  aria-label={`Stress sparkline for ${a.name}`}
                  viewBox="0 0 60 18"
                  preserveAspectRatio="none"
                  data-testid={`sparkline-${a.name}`}
                >
                  {a.spark ? (
                    <polyline
                      fill="none"
                      stroke={a.stress}
                      strokeWidth="2"
                      points={a.spark}
                    />
                  ) : null}
                </svg>
              </div>
            </div>
            <div className={styles.meta}>
              {/* Keep legacy textual line for backward-compatibility with existing tests */}
              <div>
                avg stress {formatNum(a.avg)} • guardrails {a.guardrail} • context {a.context}
                {a.cause ? ` • cause ${a.cause}` : ""}
              </div>
              {/* New visual badges */}
              <span className={styles.badges}>
                <span className={styles.badge} title="Guardrails" data-testid={`badge-g-${a.name}`}>G: {a.guardrail}</span>
                <span className={styles.badge} title="Context" data-testid={`badge-c-${a.name}`}>C: {a.context}</span>
              </span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
