import styles from "./DayStoryboardList.module.css";
import type { DayStoryboardItemViewModel, StoryboardItem } from "../../vm/dayStoryboardVm";
import DayStoryboardStrip from "./DayStoryboardStrip";
import { useEffect, useMemo, useRef } from "react";

export interface DayStoryboardListProps {
  items: DayStoryboardItemViewModel[];
  selectedDayIndex: number;
  onSelectDay: (dayIndex: number) => void;
  /** Optional selection state for a specific narrative item (lane="narrative"). */
  selectedNarrativeBlockId?: string | null;
  onSelectNarrativeItem?: (item: StoryboardItem) => void;
  /** Optional token to force scroll into view even if selectedDayIndex doesn't change. */
  scrollToSelectedDayToken?: number;
  /** Phase 3C: clicking a cameo opens belief mini-panel */
  onClickCameo?: (dayIndex: number, agentName: string) => void;
}

export default function DayStoryboardList({ items, selectedDayIndex, onSelectDay, selectedNarrativeBlockId = null, onSelectNarrativeItem, scrollToSelectedDayToken, onClickCameo }: DayStoryboardListProps) {
  // Graceful null render
  if (!Array.isArray(items) || items.length === 0) {
    return null;
  }

  // Stable refs for scroll container and per-strip elements
  const containerRef = useRef<HTMLDivElement | null>(null);
  const stripRefs = useRef<Map<number, HTMLElement>>(new Map());
  // ensure known indices for quick iteration
  const dayIndices = useMemo(() => items.map((i) => i.dayIndex), [items]);

  // rAF throttled scroll handler to compute dominant day
  const scrolling = useRef(false);
  function onScroll() {
    if (scrolling.current) return;
    scrolling.current = true;
    // eslint-disable-next-line @typescript-eslint/no-misused-promises
    requestAnimationFrame(() => {
      scrolling.current = false;
      const container = containerRef.current;
      if (!container) return;
      const cRect = container.getBoundingClientRect();
      const cCenterY = cRect.top + cRect.height / 2;
      let bestIdx: number | null = null;
      let bestDist = Number.POSITIVE_INFINITY;
      for (const idx of dayIndices) {
        const el = stripRefs.current.get(idx);
        if (!el) continue;
        const r = el.getBoundingClientRect();
        const elCenter = r.top + r.height / 2;
        const dist = Math.abs(elCenter - cCenterY);
        if (dist < bestDist) {
          bestDist = dist;
          bestIdx = idx;
        }
      }
      if (bestIdx !== null && bestIdx !== selectedDayIndex) {
        onSelectDay(bestIdx);
      }
    });
  }

  // When selected day changes (via timeline or elsewhere), scroll the strip into view
  useEffect(() => {
    const el = stripRefs.current.get(selectedDayIndex) as any;
    el?.scrollIntoView?.({ block: "nearest" });
  }, [selectedDayIndex, scrollToSelectedDayToken]);

  return (
    <section aria-label="Day storyboard">
      <div className={styles.header}>Storyboard</div>
      <div
        className={styles.list}
        ref={containerRef}
        onScroll={onScroll}
        data-testid="day-storyboard-container"
        role="list"
        aria-label="Storyboard days"
      >
        {items.map((it) => (
          <div
            key={it.dayIndex}
            data-day-index={it.dayIndex}
            ref={(el) => {
              if (el) stripRefs.current.set(it.dayIndex, el);
              else stripRefs.current.delete(it.dayIndex);
            }}
            role="listitem"
          >
            <DayStoryboardStrip
              item={it}
              isSelected={selectedDayIndex === it.dayIndex}
              onSelect={onSelectDay}
              selectedNarrativeBlockId={selectedNarrativeBlockId}
              onSelectNarrativeItem={onSelectNarrativeItem}
              onClickCameo={onClickCameo}
            />
          </div>
        ))}
      </div>
    </section>
  );
}
