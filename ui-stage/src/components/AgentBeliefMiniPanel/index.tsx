import styles from "./AgentBeliefMiniPanel.module.css";

export interface AgentBeliefMiniPanelProps {
  dayIndex: number;
  agentName: string;
  beliefText?: string | null;
  whatHappened: string;
}

export default function AgentBeliefMiniPanel({ dayIndex, agentName, beliefText, whatHappened }: AgentBeliefMiniPanelProps) {
  const aria = `Belief versus outcome for ${agentName} on Day ${dayIndex}`;
  return (
    <div className={styles.panel} role="group" aria-label={aria} data-testid="agent-belief-mini-panel">
      <div className={styles.title}>How {agentName} saw it</div>
      <div className={styles.body}>
        {beliefText && String(beliefText).trim().length > 0 ? beliefText : "No explicit belief recorded for this day."}
      </div>
      <div className={styles.misalign} aria-hidden>
        ⇄
      </div>
      <div className={styles.sectionTitle}>What actually happened</div>
      <div className={styles.body}>{whatHappened}</div>
    </div>
  );
}
