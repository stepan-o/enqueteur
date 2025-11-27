import type { StageNarrativeBlock } from "../../types/stage";
import styles from "./NarrativeBlockV2.module.css";

export interface NarrativeBlockV2Props {
  block: StageNarrativeBlock;
  /**
   * When true, hides any tag that is identical (case-insensitive) to the block kind.
   * Useful for top-level narrative where tags often duplicate the kind label,
   * which can confuse text queries in tests.
   */
  dedupeKindTag?: boolean;
}

function iconForKind(kind: string): string {
  const k = (kind || "").toLowerCase();
  if (k.includes("recap")) return "▣";
  if (k.includes("beat")) return "●";
  if (k.includes("aside")) return "◦";
  if (k.includes("supervisor")) return "◆";
  if (k.includes("intro")) return "▮";
  if (k.includes("outro")) return "▯";
  return "●";
}

function moodClass(tags: unknown): string | undefined {
  const list = Array.isArray(tags) ? (tags as string[]).map((t) => (t || "").toLowerCase()) : [];
  if (list.includes("conflict")) return styles.moodConflict;
  if (list.includes("confusion")) return styles.moodConfusion;
  if (list.includes("cooperation") || list.includes("ally") || list.includes("support")) return styles.moodCooperation;
  return undefined;
}

export default function NarrativeBlockV2({ block, dedupeKindTag = false }: NarrativeBlockV2Props) {
  const kind = typeof block?.kind === "string" ? block.kind : "";
  const text = typeof block?.text === "string" ? block.text : "";
  const tags = Array.isArray(block?.tags) ? (block.tags as string[]) : [];
  const dayIndex = typeof block?.day_index === "number" ? block.day_index : null;
  const agentName = typeof block?.agent_name === "string" ? block.agent_name : null;

  const mood = moodClass(tags);
  const filteredTags = dedupeKindTag
    ? tags.filter((t) => (t || "").toLowerCase() !== (kind || "").toLowerCase())
    : tags;

  return (
    <div className={[styles.root, mood].filter(Boolean).join(" ")} data-testid="narrative-block" data-variant="v2" title={text}>
      <div className={styles.row}>
        <div className={styles.icon} aria-hidden>{iconForKind(kind)}</div>
        <div className={styles.content}>
          <div className={styles.kind}>{kind}</div>
          <div className={styles.text}>{text}</div>
          {filteredTags.length > 0 && (
            <div className={styles.tags} aria-label="tags">
              {filteredTags.map((t, i) => (
                <span key={`${t}-${i}`} className={styles.tag}>{t}</span>
              ))}
            </div>
          )}
          {(dayIndex !== null || agentName) && (
            <div className={styles.meta}>
              {dayIndex !== null ? `Day ${dayIndex}` : ""}
              {dayIndex !== null && agentName ? " • " : ""}
              {agentName ? `Agent ${agentName}` : ""}
            </div>
          )}
        </div>
        <div className={styles.right}>
          {/* reserve spot for tiny badges if needed later, kept minimal now */}
        </div>
      </div>
    </div>
  );
}
