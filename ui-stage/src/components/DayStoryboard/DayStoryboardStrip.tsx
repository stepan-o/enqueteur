import styles from "./DayStoryboardStrip.module.css";
import type { DayStoryboardItemViewModel, StoryboardItem } from "../../vm/dayStoryboardVm";

export interface DayStoryboardStripProps {
  item: DayStoryboardItemViewModel;
  isSelected: boolean;
  onSelect: (dayIndex: number) => void;
  selectedNarrativeBlockId?: string | null;
  onSelectNarrativeItem?: (item: StoryboardItem) => void;
}

export default function DayStoryboardStrip({ item, isSelected, onSelect, selectedNarrativeBlockId = null, onSelectNarrativeItem }: DayStoryboardStripProps) {
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
      {/* Lanes container — starting with Narrative lane only */}
      <div className={styles.lanes} aria-label="Storyboard lanes">
        <div className={styles.laneRow} aria-label="Narrative lane">
          <div className={styles.laneLabel}>Narrative</div>
          <div className={styles.laneStrip} role="list" aria-label={`Day ${item.dayIndex} narrative items`}>
            {(Array.isArray((item as any).narrativeLane) ? item.narrativeLane : []).map((n) => {
              const isItemSelected = selectedNarrativeBlockId
                ? selectedNarrativeBlockId === n.blockId
                : isSelected; // when no specific block selected, highlight items of selected day
              const cls = isItemSelected
                ? `${styles.laneItem} ${styles.laneItemSelected}`
                : styles.laneItem;
              return (
                <button
                  key={n.blockId}
                  type="button"
                  className={cls}
                  role="listitem"
                  data-lane="narrative"
                  data-block-id={n.blockId}
                  data-selected={isItemSelected ? "true" : "false"}
                  aria-label={`Narrative: ${n.kind} — ${n.text}`}
                  title={n.text}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onSelectNarrativeItem) {
                      onSelectNarrativeItem(n);
                    } else {
                      onSelect(item.dayIndex);
                    }
                  }}
                >
                  {n.kind}
                </button>
              );
            })}
          </div>
        </div>
      </div>
      <span className={styles.sparklineBox} aria-hidden />
    </button>
  );
}
