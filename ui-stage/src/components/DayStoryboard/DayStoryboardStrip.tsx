import styles from "./DayStoryboardStrip.module.css";
import type { DayStoryboardItemViewModel } from "../../vm/dayStoryboardVm";

export interface DayStoryboardStripProps {
  item: DayStoryboardItemViewModel;
  isSelected: boolean;
  onSelect: (dayIndex: number) => void;
}

export default function DayStoryboardStrip({ item, isSelected, onSelect }: DayStoryboardStripProps) {
  const className = isSelected ? `${styles.strip} ${styles.selected}` : styles.strip;
  return (
    <button
      type="button"
      className={className}
      data-testid={`day-storyboard-strip-${item.dayIndex}`}
      data-selected={isSelected ? "true" : "false"}
      onClick={() => onSelect(item.dayIndex)}
      aria-pressed={isSelected}
      title={`${item.label}`}
    >
      <span className={styles.pill}>{item.label}</span>
      <span className={styles.caption}>{item.caption}</span>
      <span className={styles.sparklineBox} aria-hidden />
    </button>
  );
}
