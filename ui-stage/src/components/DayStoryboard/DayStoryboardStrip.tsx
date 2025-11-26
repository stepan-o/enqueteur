import styles from "./DayStoryboardStrip.module.css";
import type { DayStoryboardItemViewModel, StoryboardItem } from "../../vm/dayStoryboardVm";
import AgentAvatar from "../AgentAvatar";

export interface DayStoryboardStripProps {
  item: DayStoryboardItemViewModel;
  isSelected: boolean;
  onSelect: (dayIndex: number) => void;
  selectedNarrativeBlockId?: string | null;
  onSelectNarrativeItem?: (item: StoryboardItem) => void;
  onClickCameo?: (dayIndex: number, agentName: string) => void;
}

export default function DayStoryboardStrip({ item, isSelected, onSelect, selectedNarrativeBlockId = null, onSelectNarrativeItem, onClickCameo }: DayStoryboardStripProps) {
  const band = (item as any).tensionBandClass as
    | "tensionLow"
    | "tensionMedium"
    | "tensionHigh"
    | undefined;
  const bandClass = band ? (styles as any)[band] : undefined;
  const base = [styles.strip, bandClass, isSelected ? styles.selected : undefined]
    .filter(Boolean)
    .join(" ");

  const spark = Array.isArray((item as any).sparklinePoints)
    ? ((item as any).sparklinePoints as number[])
    : [];

  function trendSummary(points: number[]): string {
    if (!points || points.length < 2) return "steady";
    const first = points[0];
    const last = points[points.length - 1];
    const mean = points.reduce((a, b) => a + b, 0) / points.length;
    const variance = points.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / points.length;
    const stdev = Math.sqrt(variance);
    const delta = last - first;
    if (stdev < 0.05 && Math.abs(delta) < 0.03) return "steady";
    if (delta > 0.05) return "rising";
    if (delta < -0.05) return "easing";
    return "fluctuating";
  }

  const trendLabel = `Tension trend for ${item.label}: ${trendSummary(spark)}`;
  return (
    <button
      type="button"
      className={base}
      data-testid={`day-storyboard-strip-${item.dayIndex}`}
      data-band={band || undefined}
      data-selected={isSelected ? "true" : "false"}
      onClick={() => onSelect(item.dayIndex)}
      aria-pressed={isSelected}
      aria-selected={isSelected}
      title={`${item.label}`}
    >
      <span className={styles.pill}>{item.label}</span>
      <span className={styles.caption}>{item.caption}</span>
      {/* Agent cameos cluster (Phase 3C) */}
      {Array.isArray((item as any).agentCameos) && (item as any).agentCameos!.length > 0 ? (
        <span className={styles.cameos} aria-label={`Agent cameos for ${item.label}`}>
          {(item.agentCameos || []).slice(0, 3).map((c) => (
            <span
              key={`${item.dayIndex}-${c.name}`}
              role="button"
              tabIndex={0}
              className={styles.cameoBtn}
              aria-label={`View ${c.name}'s view of ${item.label}`}
              title={`View ${c.name}'s view of ${item.label}`}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onClickCameo && onClickCameo(item.dayIndex, c.name);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  e.stopPropagation();
                  onClickCameo && onClickCameo(item.dayIndex, c.name);
                }
              }}
            >
              <AgentAvatar name={c.name} vibeColorKey={c.vibeColorKey as any} stressTier={c.stressTier === "high" ? "high" : c.stressTier === "mid" ? "medium" : "none"} size="sm" />
            </span>
          ))}
          {((item as any).agentCameoOverflowCount || 0) > 0 ? (
            <span className={styles.overflowPill} title={`${(item as any).agentCameoOverflowCount} more agents involved`}>
              +{(item as any).agentCameoOverflowCount}
            </span>
          ) : null}
        </span>
      ) : null}
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
      {/* Treat sparkline box as an image for accessibility so getByLabelText works on its aria-label */}
      <span
        className={styles.sparklineBox}
        role="img"
        aria-label={trendLabel}
        data-testid={`day-sparkline-${item.dayIndex}`}
      >
        {spark.length >= 2 ? (
          <svg className={styles.sparklineSvg} viewBox="0 0 76 18" role="img" aria-hidden>
            {(() => {
              // Map normalized points [0,1] to SVG coords; y inverted (0 at bottom)
              const w = 76;
              const h = 18;
              const n = spark.length;
              const step = n > 1 ? w / (n - 1) : w;
              const toY = (v: number) => h - v * (h - 2) - 1; // small padding
              const d = spark
                .map((v, i) => `${i === 0 ? "M" : "L"}${i * step},${toY(v)}`)
                .join(" ");
              return <path className={styles.sparklinePath} d={d} />;
            })()}
          </svg>
        ) : null}
      </span>
    </button>
  );
}
