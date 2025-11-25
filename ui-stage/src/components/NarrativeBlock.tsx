import type { StageNarrativeBlock } from "../types/stage";
import styles from "./NarrativeBlock.module.css";

export interface NarrativeBlockProps {
  block: StageNarrativeBlock;
}

export default function NarrativeBlock({ block }: NarrativeBlockProps) {
  const kind = typeof block?.kind === "string" ? block.kind : "";
  const text = typeof block?.text === "string" ? block.text : "";
  const tags = Array.isArray(block?.tags) ? (block.tags as string[]) : [];
  const dayIndex = typeof block?.day_index === "number" ? block.day_index : null;
  const agentName = typeof block?.agent_name === "string" ? block.agent_name : null;

  return (
    <div className={styles.block} data-testid="narrative-block">
      <div>
        <span className={styles.kind}>{kind}</span>
        <span className={styles.text}>{text}</span>
        {tags.length > 0 && (
          <span className={styles.tags} aria-label="tags">
            {tags.map((t, i) => (
              <span key={`${t}-${i}`} className={styles.tag}>{t}</span>
            ))}
          </span>
        )}
      </div>
      {(dayIndex !== null || agentName) && (
        <small className={styles.meta}>
          {dayIndex !== null ? `Day ${dayIndex}` : ""}
          {dayIndex !== null && agentName ? " • " : ""}
          {agentName ? `Agent ${agentName}` : ""}
        </small>
      )}
    </div>
  );
}
