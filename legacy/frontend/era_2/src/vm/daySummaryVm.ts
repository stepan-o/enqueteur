import type { EpisodeViewModel } from "./episodeVm";
import { buildDayDetail } from "./dayDetailVm";

export interface DaySummaryViewModel {
  dayIndex: number;
  tensionDirection: "up" | "down" | "flat" | "unknown";
  tensionChange: number | null;
  primaryAgentName: string | null;
  primaryAgentStress: number | null;
  notableText: string;
}

function directionFromDelta(delta: number | null): {
  dir: "up" | "down" | "flat" | "unknown";
} {
  if (delta === null) return { dir: "unknown" };
  if (delta > 0.05) return { dir: "up" };
  if (delta < -0.05) return { dir: "down" };
  return { dir: "flat" };
}

export function buildDaySummary(
  episode: EpisodeViewModel,
  dayIndex: number
): DaySummaryViewModel {
  const trend: number[] | undefined = (episode as any)?._raw?.tension_trend;

  let delta: number | null = null;
  if (Array.isArray(trend) && dayIndex > 0 && trend.length > dayIndex) {
    const current = trend[dayIndex];
    const prev = trend[dayIndex - 1];
    if (typeof current === "number" && typeof prev === "number") {
      delta = current - prev;
    }
  }

  const { dir } = directionFromDelta(delta);

  // Determine primary agent by highest avgStress using day detail (which normalizes nulls)
  const detail = buildDayDetail(episode, dayIndex);
  const sortedByStress = [...detail.agents].sort(
    (a, b) => (b.avgStress ?? 0) - (a.avgStress ?? 0)
  );
  const top = sortedByStress[0];
  const primaryAgentName = top ? top.name : null;
  const primaryAgentStress = top ? top.avgStress : null;

  // Build notableText with stable templates
  const prevLabel = dayIndex > 0 ? `Day ${dayIndex - 1}` : "yesterday";
  const agentClause = primaryAgentName
    ? `, with ${primaryAgentName} carrying the highest stress (${(primaryAgentStress ?? 0).toFixed(2)}).`
    : ".";

  let notableText: string;
  switch (dir) {
    case "up":
      notableText = `Tension rose compared to ${prevLabel}${agentClause}`;
      break;
    case "down":
      notableText = `Tension fell compared to ${prevLabel}${agentClause}`;
      break;
    case "flat":
      notableText = `Tension held steady compared to ${prevLabel}${agentClause}`;
      break;
    case "unknown":
    default: {
      if (primaryAgentName) {
        notableText = `Tension was moderate, with ${primaryAgentName} carrying the highest stress (${(primaryAgentStress ?? 0).toFixed(2)}).`;
      } else {
        notableText = "Tension was moderate.";
      }
      break;
    }
  }

  return {
    dayIndex,
    tensionDirection: dir,
    tensionChange: delta,
    primaryAgentName,
    primaryAgentStress,
    notableText,
  };
}
