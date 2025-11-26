import React from "react";
import styles from "./StageMap.module.css";
import type { StageMapViewModel } from "../../vm/stageMapVm";

export interface StageMapProps {
  viewModel: StageMapViewModel;
  selectedDayIndex: number | null;
}

function getDay(vm: StageMapViewModel, idx: number | null) {
  if (idx == null) return null;
  const day = vm.days.find((d) => d.dayIndex === idx) ?? null;
  return day ?? null;
}

export default function StageMap({ viewModel, selectedDayIndex }: StageMapProps) {
  const day = getDay(viewModel, selectedDayIndex);
  const ariaLabel = "Stage map";

  if (!day) {
    // Render neutral map using union of rooms from all days (Phase 4A synthetic → one room)
    const roomLabels = collectStableRoomLabels(viewModel);
    return (
      <div role="group" aria-label={ariaLabel}>
        <div className={styles.caption}>No day selected</div>
        <div className={styles.root} data-selected="false">
          {roomLabels.map((label) => (
            <div
              key={label}
              className={styles.tile}
              data-tension-tier="low"
              role="img"
              aria-label={`${label}, low tension, 0 agents active`}
            >
              <div className={styles.roomLabel}>{label}</div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div role="group" aria-label={ariaLabel}>
      <div className={styles.root} data-selected="true">
        {day.rooms.map((r) => (
          <div
            key={r.id}
            className={styles.tile}
            data-tension-tier={day.tensionTier}
            role="img"
            aria-label={`${r.label}, ${day.tensionTier} tension, ${agentSummary(r.primaryAgents)} on Day ${day.dayIndex}`}
          >
            <div className={styles.roomLabel}>{r.label}</div>
            {r.primaryAgents.length > 0 ? (
              <div className={styles.agents} aria-label="agents">
                {r.primaryAgents.slice(0, 3).map((name) => (
                  <span key={name} className={styles.chip} title={name}>
                    {initials(name)}
                  </span>
                ))}
              </div>
            ) : null}
            <div className={styles.meta}>
              incidents {r.incidentCount}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function initials(name: string): string {
  const parts = name.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const first = parts[0][0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] ?? "" : "";
  return (first + last).toUpperCase();
}

function agentSummary(names: string[]): string {
  const n = names.length;
  if (n === 0) return "0 agents active";
  if (n === 1) return "1 agent active";
  return `${n} agents active`;
}

function collectStableRoomLabels(vm: StageMapViewModel): string[] {
  const labels = new Set<string>();
  for (const d of vm.days || []) {
    for (const r of d.rooms || []) labels.add(r.label);
  }
  if (labels.size === 0) labels.add("Factory Floor");
  return Array.from(labels).sort((a, b) => a.localeCompare(b));
}
