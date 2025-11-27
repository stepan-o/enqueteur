import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useEpisodeLoader } from "../hooks/useEpisodeLoader";
import type { EpisodeViewModel } from "../vm/episodeVm";
import EpisodeHeader from "../components/EpisodeHeader";
import TimelineStrip from "../components/TimelineStrip";
import { buildStageMapView } from "../vm/stageMapVm";
import StageMap from "../components/StageMap";
import { buildPanelAgents } from "../vm/agentVm";
import AgentAvatar from "../components/AgentAvatar";
import styles from "./StageView.module.css";

export default function StageView() {
  const { id } = useParams();
  const { episode, error, isLoading } = useEpisodeLoader();

  // Selected indices/state
  const [selectedDayIndex, setSelectedDayIndex] = useState<number | null>(null);
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);
  const [selectedAgentName, setSelectedAgentName] = useState<string | null>(null);

  // When episode loads, default to first day if available
  useEffect(() => {
    if (!episode) return;
    const first = (episode.days || [])[0];
    setSelectedDayIndex(first ? first.index : null);
    setSelectedRoomId(null);
    setSelectedAgentName(null);
  }, [episode]);

  // Build VMs regardless; they will be unused if episode is null
  const stageMapVM = useMemo(() => (episode ? buildStageMapView(episode as EpisodeViewModel) : { days: [] }), [episode]);
  const hasSelectedDay =
    selectedDayIndex != null && stageMapVM.days.some((d) => d.dayIndex === selectedDayIndex);
  const effectiveDayIndex = hasSelectedDay ? (selectedDayIndex as number) : null;
  const stageMapLabel = hasSelectedDay
    ? `Stage map for Day ${effectiveDayIndex}`
    : "Stage map (no day selected)";

  // Derive detail panel content helpers
  const dayVM = hasSelectedDay
    ? stageMapVM.days.find((d) => d.dayIndex === effectiveDayIndex) || null
    : null;
  const allPrimaryAgents = dayVM
    ? Array.from(new Set(dayVM.rooms.flatMap((r) => r.primaryAgents)))
    : [];
  const panelAgents = useMemo(() => (episode ? buildPanelAgents(episode) : []), [episode]);
  const agentByName = useMemo(
    () => Object.fromEntries(panelAgents.map((a) => [a.name, a])),
    [panelAgents]
  );

  function clearSelection() {
    setSelectedAgentName(null);
    setSelectedRoomId(null);
  }

  return (
    <main role="main" className={styles.page} aria-label="Stage View">
      {/* Top bar */}
      <div className={styles.topBar}>
        {episode ? <EpisodeHeader episode={episode} /> : <div>Loading…</div>}
        <div>
          <a href={id ? `/episodes/${id}` : "/"}>← Back to Latest View</a>
        </div>
        {episode ? (
          <div>
            <TimelineStrip
              days={episode.days}
              selectedIndex={hasSelectedDay ? (effectiveDayIndex as number) : (episode.days[0]?.index ?? 0)}
              onSelect={(idx) => {
                setSelectedDayIndex(idx);
                setSelectedAgentName(null);
                setSelectedRoomId(null);
              }}
              daySummaries={episode.daySummaries}
            />
          </div>
        ) : null}
      </div>

      {/* Main grid */}
      <div className={styles.mainGrid}>
        <section className={styles.stageMapPanel} role="region" aria-label={stageMapLabel}>
          <StageMap
            viewModel={stageMapVM}
            selectedDayIndex={effectiveDayIndex}
            selectedRoomId={selectedRoomId}
            onRoomClick={(roomId) => setSelectedRoomId(roomId)}
            onAgentClick={(name) => setSelectedAgentName(name)}
          />
        </section>

        <aside className={styles.detailPanel} aria-label="Stage details panel" role="complementary">
          <div
            className={`${styles.detailHeaderBand} ${selectedAgentName ? styles.detailHeaderAgent : styles.detailHeaderWorld}`}
          >
            {selectedAgentName ? "Agent focus" : "World view"}
          </div>
          <div className={styles.detailBody}>
            {!episode || !hasSelectedDay ? (
              <div className={styles.summaryText}>No days available for this episode.</div>
            ) : selectedAgentName ? (
              <AgentFocus
                agentName={selectedAgentName}
                agentVM={agentByName[selectedAgentName]}
                onClear={clearSelection}
              />
            ) : (
              <WorldSummary
                dayIndex={effectiveDayIndex as number}
                roomLabel={dayVM?.rooms[0]?.label || "Factory Floor"}
                tensionTier={dayVM?.tensionTier || "low"}
                incidents={dayVM?.rooms[0]?.incidentCount || 0}
                agents={allPrimaryAgents}
                onClear={clearSelection}
              />
            )}
          </div>
        </aside>
      </div>
    </main>
  );
}

function WorldSummary({
  dayIndex,
  roomLabel,
  tensionTier,
  incidents,
  agents,
  onClear,
}: {
  dayIndex: number;
  roomLabel: string;
  tensionTier: "low" | "medium" | "high";
  incidents: number;
  agents: string[];
  onClear: () => void;
}) {
  return (
    <div>
      <div className={styles.summaryText}>
        Tension is {tensionTier} for {roomLabel} on Day {dayIndex}.
      </div>
      <div className={styles.summaryText}>
        Incidents {incidents} • agents: {agents.join(", ") || "none"}
      </div>
      <div className={styles.controls}>
        <button type="button" onClick={onClear}>Clear selection</button>
      </div>
    </div>
  );
}

function AgentFocus({
  agentName,
  agentVM,
  onClear,
}: {
  agentName: string;
  agentVM: ReturnType<typeof buildPanelAgents>[number] | undefined;
  onClear: () => void;
}) {
  if (!agentVM) {
    return (
      <div data-testid="agent-focus-panel">
        <div className={styles.summaryText}>Agent {agentName}</div>
        <div className={styles.controls}>
          <button type="button" onClick={onClear}>Clear selection</button>
        </div>
      </div>
    );
  }
  return (
    <div data-testid="agent-focus-panel">
      <div className={styles.agentRow}>
        <AgentAvatar name={agentVM.name} vibeColorKey={agentVM.vibeColorKey} stressTier={agentVM.stressTier} size="md" />
        <div>
          <div className={styles.agentName}>{agentVM.name}</div>
          <div className={styles.agentRole}>{agentVM.role}</div>
        </div>
      </div>
      <div className={`${styles.summaryText} ${styles.agentStats}`}>
        avg stress {(agentVM.avgStress ?? 0).toFixed(2)} • guardrails {agentVM.guardrailTotal} • context {agentVM.contextTotal}
      </div>
      {agentVM.displayTagline ? (
        <div className={styles.agentTagline}>{agentVM.displayTagline}</div>
      ) : null}
      <div className={styles.controls}>
        <button type="button" onClick={onClear}>Clear selection</button>
      </div>
    </div>
  );
}
