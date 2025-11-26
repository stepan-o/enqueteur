import styles from "./AgentAvatarV1.module.css";
import { colorForVibe } from "../../style-maps/vibeColors";

/**
 * Legacy Avatar Component — AgentAvatarV1
 *
 * This component predates Era II Phase 3 identity work. It renders a simple
 * letter-in-circle avatar with a background derived from legacy "vibe" colors.
 *
 * New UI should prefer AgentAvatar (v2) in ui-stage/src/components/AgentAvatar,
 * which uses vibeColorKey + stressTier and Era II identity tokens for ring/glow.
 *
 * AgentAvatarV1 remains for compatibility in places like DayDetailPanel and
 * associated tests. Please migrate callsites opportunistically in future work.
 */

export interface AgentAvatarV1Props {
  name: string;
  role: string;
  vibe: string;
  visual: string; // reserved for future illustrated avatars
  size?: "sm" | "md" | "lg";
  /**
   * When false, suppresses rendering of the visible initial character.
   * Useful when a parent provides its own visible initial for legacy tests.
   */
  showInitial?: boolean;
}

function initialFrom(source: string): string {
  const ch = (source || "?").trim().charAt(0);
  return ch ? ch.toUpperCase() : "?";
}

export default function AgentAvatarV1({
  name,
  role,
  vibe,
  visual,
  size = "md",
  showInitial = true,
}: AgentAvatarV1Props) {
  const bg = colorForVibe(vibe);
  const initial = initialFrom(name || visual);
  const sizeClass = size === "lg" ? styles.lg : size === "sm" ? styles.sm : styles.md;
  const roleAttr = (role || "").toLowerCase();

  return (
    <div
      className={[styles.root, sizeClass].join(" ")}
      style={{ backgroundColor: bg }}
      aria-label={`Agent avatar for ${name}, role: ${role}`}
      data-role={roleAttr}
      data-size={size}
      data-testid="agent-avatar-v1"
    >
      {showInitial ? (
        <span className={styles.initial} aria-hidden>
          {initial}
        </span>
      ) : null}
    </div>
  );
}
