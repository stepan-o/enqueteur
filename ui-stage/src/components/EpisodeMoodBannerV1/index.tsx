import styles from "./EpisodeMoodBannerV1.module.css";
import type { EpisodeArcMoodViewModel } from "../../vm/episodeArcMoodVm";

export interface EpisodeMoodBannerProps {
  mood: EpisodeArcMoodViewModel;
}

export default function EpisodeMoodBannerV1({ mood }: EpisodeMoodBannerProps) {
  if (!mood || !mood.tensionClass) return null;
  const cls = [styles.banner, (styles as any)[mood.tensionClass] || ""].join(" ").trim();
  // Clarify that this is an episode-wide arc indicator, not day-to-day direction.
  const aria = `Episode arc mood: ${mood.label}. Episode-wide summary: ${mood.summaryLine}`;
  return (
    <div className={cls} data-testid="episode-mood-banner">
      <div className={styles.row}>
        <span className={styles.icon} role="img" aria-label={aria} aria-hidden={false}>
          {mood.icon}
        </span>
        <div>
          <div className={styles.label}>{mood.label}</div>
          <div className={styles.summary}>{mood.summaryLine}</div>
        </div>
      </div>
    </div>
  );
}
