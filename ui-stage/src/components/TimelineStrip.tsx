import type { DayViewModel } from "../vm/dayVm";
import styles from "./TimelineStrip.module.css";

export interface TimelineStripProps {
  days: DayViewModel[];
  selectedIndex: number;
  onSelect: (index: number) => void;
}

export default function TimelineStrip({
  days,
  selectedIndex,
  onSelect,
}: TimelineStripProps) {
  if (!days || days.length === 0) {
    return <div className={styles.strip} />;
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
          </button>
        );
      })}
    </div>
  );
}
