import styles from "./AgentAvatar.module.css";

export type VibeKey = "teal" | "indigo" | "green" | "amber" | "neutral";
export type StressTier = "none" | "medium" | "high" | "cooldown";

export interface AgentAvatarProps {
  name?: string;
  vibeColorKey?: VibeKey;
  stressTier?: StressTier;
  size?: "sm" | "md" | "lg";
}

function classForVibe(v: VibeKey | undefined): string {
  switch (v) {
    case "teal":
    case "indigo":
    case "green":
    case "amber":
    case "neutral":
      return styles[`vibe-${v}` as const] || styles["vibe-neutral"];
    default:
      return styles["vibe-neutral"];
  }
}

function classForStress(t: StressTier | undefined): string {
  switch (t) {
    case "medium":
      return styles["stress-medium"];
    case "high":
      return styles["stress-high"];
    case "cooldown":
      return styles["stress-cooldown"];
    case "none":
    default:
      return styles["stress-none"];
  }
}

/**
 * AgentAvatar v2 — circular frame + organic blob; uses CSS tokens for colors/glow.
 * Note: data-testid and data-size mirror v1 for backward test compatibility.
 */
export default function AgentAvatar({
  name,
  vibeColorKey = "neutral",
  stressTier = "none",
  size = "lg",
}: AgentAvatarProps) {
  const aria = name
    ? `Agent avatar for ${name}. Vibe: ${vibeColorKey}. Stress: ${stressTier}.`
    : "Agent avatar";
  const vibeClass = classForVibe(vibeColorKey);
  const stressClass = classForStress(stressTier);
  const sizeClass = size === "sm" ? styles.sm : size === "md" ? styles.md : styles.lg;

  // Simple organic blob path (static) — visually soft
  const blobPath = "M28 12c4 2 6 6 5 10-1 5-5 8-9 9-4 1-9-1-12-4-3-3-4-8-2-12 2-4 6-7 10-7 3 0 6 1 8 4z";

  return (
    <div
      className={[styles.root, vibeClass, stressClass, sizeClass].join(" ")}
      role="img"
      aria-label={aria}
      data-testid="agent-avatar-v1"
      data-size={size}
    >
      <svg className={styles.svg} viewBox="0 0 40 40" aria-hidden>
        <circle className={styles.ring} cx="20" cy="20" r="18" />
        <path className={styles.blob} d={blobPath} transform="translate(-2,-2)" />
      </svg>
    </div>
  );
}
