// ui-stage/src/utils/stressColor.ts
// Deterministic, pure color mapping for stress scores (gentler palette mirrors tensionColor thresholds)

/**
 * Map a stress score in [0,1] to a stepped color.
 * Invalid inputs (null/undefined/NaN) clamp to lowest bucket (blue).
 */
export function stressColor(score: number): string {
  const v = Number.isFinite(score) ? score : 0;
  if (v <= 0.15) return "#4FA3FF"; // cool blue
  if (v <= 0.30) return "#FFD93D"; // mild yellow
  if (v <= 0.50) return "#FF9F1C"; // warm orange
  return "#E44040"; // high red
}

export default stressColor;
