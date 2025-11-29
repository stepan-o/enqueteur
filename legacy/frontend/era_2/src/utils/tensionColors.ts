// ui-stage/src/utils/tensionColors.ts
// Deterministic, pure color mapping for tension scores.

/**
 * Map a tension score in [0,1] to a stepped color.
 * Invalid inputs (null/undefined/NaN) clamp to lowest bucket (blue).
 */
export function tensionColor(score: number): string {
  const v = typeof score === "number" && Number.isFinite(score) ? score : 0;
  if (v <= 0.15) return "#4FA3FF"; // cool blue
  if (v <= 0.30) return "#FFD93D"; // mild yellow
  if (v <= 0.50) return "#FF9F1C"; // warm orange
  return "#E44040"; // high red
}

export default tensionColor;
