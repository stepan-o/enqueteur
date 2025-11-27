export const vibeColors: Record<string, string> = {
  calm: "var(--lf-vibe-calm)",
  tense: "var(--lf-vibe-tense)",
  analytic: "var(--lf-vibe-analytic)",
  earnest: "var(--lf-vibe-earnest)",
  chaotic: "var(--lf-vibe-chaotic)",
  neutral: "var(--lf-vibe-neutral)",
};

export function colorForVibe(vibe: unknown): string {
  const key = typeof vibe === "string" ? vibe.toLowerCase() : "neutral";
  return vibeColors[key] || vibeColors.neutral;
}
