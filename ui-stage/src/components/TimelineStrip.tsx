import type { DayViewModel } from "../vm/dayVm";

export interface TimelineStripProps {
  days: DayViewModel[];
  tensionTrend: number[];
  selectedIndex: number | null;
  onSelect?: (index: number) => void;
}

export default function TimelineStrip({
  days,
  tensionTrend,
  selectedIndex,
  onSelect,
}: TimelineStripProps) {
  if (!days.length) {
    return <div className="timeline-strip empty">No days in this episode.</div>;
  }

  return (
    <div className="timeline-strip">
      <ul>
        {days.map((day, idx) => {
          const tension = tensionTrend[idx] ?? day.tensionScore;
          const isSelected = selectedIndex === day.index || selectedIndex === idx;

          return (
            <li key={day.index} onClick={() => onSelect?.(day.index)}>
              <button
                type="button"
                data-testid={`timeline-day-${day.index}`}
                aria-selected={isSelected}
                className={isSelected ? "timeline-day selected" : "timeline-day"}
                onClick={() => onSelect?.(day.index)}
              >
                <span className="timeline-day-label">Day {day.index}</span>{" "}
                <span className="timeline-day-tension">tension: {tension.toFixed(2)}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
