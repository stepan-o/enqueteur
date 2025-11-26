import styles from "./DayStoryboardList.module.css";
import type { DayStoryboardItemViewModel } from "../../vm/dayStoryboardVm";
import DayStoryboardStrip from "./DayStoryboardStrip";

export interface DayStoryboardListProps {
  items: DayStoryboardItemViewModel[];
  selectedDayIndex: number;
  onSelectDay: (dayIndex: number) => void;
}

export default function DayStoryboardList({ items, selectedDayIndex, onSelectDay }: DayStoryboardListProps) {
  if (!Array.isArray(items) || items.length === 0) {
    return null;
  }
  return (
    <section aria-label="Day storyboard">
      <div className={styles.header}>Storyboard</div>
      <div className={styles.list}>
        {items.map((it) => (
          <DayStoryboardStrip
            key={it.dayIndex}
            item={it}
            isSelected={selectedDayIndex === it.dayIndex}
            onSelect={onSelectDay}
          />)
        )}
      </div>
    </section>
  );
}
