import type { DayViewModel } from "../vm/dayVm";
import type { DaySummaryViewModel } from "../vm/daySummaryVm";
import styles from "./TimelineStrip.module.css";

export interface TimelineStripProps {
  days: DayViewModel[];
  selectedIndex: number;
  onSelect: (index: number) => void;
  daySummaries?: DaySummaryViewModel[];
}

export default function TimelineStrip({
  days,
  selectedIndex,
  onSelect,
  daySummaries,
}: TimelineStripProps) {
  if (!days || days.length === 0) {
    return <div className={styles.strip} />;
  }

  // Pre-index summaries by dayIndex for stable O(1) lookups
  const summaryByDay: Map<number, DaySummaryViewModel> | null = Array.isArray(
    daySummaries
  )
    ? new Map(daySummaries.map((s) => [s.dayIndex, s]))
    : null;

  function renderSummary(dayIndex: number) {
    if (!summaryByDay) return null;
    const s = summaryByDay.get(dayIndex);
    if (!s) return null;
    // Only render for known directions
    let symbol = "";
    let cls: string | undefined;
    switch (s.tensionDirection) {
      case "up":
        symbol = "▲";
        cls = styles.up;
        break;
      case "down":
        symbol = "▼";
        cls = styles.down;
        break;
      case "flat":
        symbol = "▬";
        cls = styles.flat;
        break;
      default:
        return null; // unknown → no indicator
    }
    const agent = s.primaryAgentName ? ` ${s.primaryAgentName}` : "";
    const className = cls ? `${styles.summary} ${cls}` : styles.summary;
    return (
      <span className={className} aria-hidden>
        {symbol}
        {agent}
      </span>
    );
  }

  return (
    <div className={styles.strip} role="group" aria-label="Episode timeline">
      {days.map((d) => {
        const isSelected = selectedIndex === d.index;
        const className = isSelected
          ? `${styles.day} ${styles.selected}`
          : styles.day;
        return (
          <button
            key={d.index}
            type="button"
            className={className}
            data-testid={`timeline-day-${d.index}`}
            aria-selected={isSelected}
            onClick={() => onSelect(d.index)}
          >
            <span className={styles.label}>{`Day ${d.index}`}</span>
            {renderSummary(d.index)}
          </button>
        );
      })}
    </div>
  );
}
