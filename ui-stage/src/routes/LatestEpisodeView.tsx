import { useEffect, useState } from "react";
import type { EpisodeViewModel } from "../vm/episodeVm";
import EpisodeHeader from "../components/EpisodeHeader";
import TimelineStrip from "../components/TimelineStrip";
import DayDetailPanel from "../components/DayDetailPanel";
import EpisodeAgentsPanel from "../components/EpisodeAgentsPanel";
import EpisodeStoryPanel from "../components/EpisodeStoryPanel";
import EpisodeNavigator from "../components/EpisodeNavigator";
import { useEpisodeLoader } from "../hooks/useEpisodeLoader";
import { buildEpisodeArcMood } from "../vm/episodeArcMoodVm";
import EpisodeMoodBannerV1 from "../components/EpisodeMoodBannerV1";
import { buildDayStoryboardItems, type StoryboardItem } from "../vm/dayStoryboardVm";
import DayStoryboardList from "../components/DayStoryboard/DayStoryboardList";
import AgentBeliefMiniPanel from "../components/AgentBeliefMiniPanel";
import { useRef } from "react";

export default function LatestEpisodeView() {
  const { episode, error, isLoading } = useEpisodeLoader();

  console.log("Render LatestEpisodeView", { episode, error, isLoading });

  const [selectedDayIndex, setSelectedDayIndex] = useState<number>(0);
  const dayDetailRef = useRef<HTMLDivElement | null>(null);
  const [selectedNarrativeBlockId, setSelectedNarrativeBlockId] = useState<string | null>(null);
  // Token to force storyboard to scroll the selected strip into view (used for timeline clicks)
  const [scrollStoryboardToken, setScrollStoryboardToken] = useState<number>(0);
  // Phase 3C: selected belief mini-panel state
  const [selectedBelief, setSelectedBelief] = useState<{
    dayIndex: number;
    agentName: string;
  } | null>(null);

  // Preserve initial selection logic: set to first day index when episode arrives
  useEffect(() => {
    if (episode) {
      if (episode.days.length > 0) {
        setSelectedDayIndex(episode.days[0].index);
      } else {
        setSelectedDayIndex(0);
      }
      // Clear belief panel on new episode
      setSelectedBelief(null);
    }
  }, [episode]);

  if (error) {
    return <div className="error">Error loading episode: {error}</div>;
  }

  // Guard rendering on episode presence; handle both loading and empty states explicitly
  if (!episode) {
    if (isLoading) {
      return <div className="loading">Loading latest StageEpisode…</div>;
    }
    return <div className="empty">No episode available.</div>;
  }

  return (
    <div>
      {(() => {
        try {
          const mood = buildEpisodeArcMood(episode as any);
          return mood ? <EpisodeMoodBannerV1 mood={mood} /> : null;
        } catch {
          return null;
        }
      })()}
      <EpisodeHeader episode={episode} />

      <EpisodeNavigator
        currentEpisodeId={episode.id}
        currentEpisodeIndex={episode.index}
      />

      {/* Day Storyboard */}
      {(() => {
        let items = [] as ReturnType<typeof buildDayStoryboardItems>;
        try {
          items = buildDayStoryboardItems(episode as any);
        } catch {
          items = [];
        }
        const handleClickCameo = (dayIndex: number, agentName: string) => {
          // Phase 3C follow-up: cameo click should NOT change selected day or scroll.
          // It only toggles the belief mini-panel.
          setSelectedNarrativeBlockId(null);
          setSelectedBelief((prev) => {
            if (prev && prev.dayIndex === dayIndex && prev.agentName === agentName) {
              return null; // toggle off
            }
            return { dayIndex, agentName };
          });
        };

        return (
          <DayStoryboardList
            items={items}
            selectedDayIndex={selectedDayIndex}
            scrollToSelectedDayToken={scrollStoryboardToken}
            onSelectDay={(idx) => {
              setSelectedDayIndex(idx);
              setSelectedNarrativeBlockId(null); // day-level selection clears specific narrative selection
              setSelectedBelief(null); // selecting a day clears belief panel
              // bonus: gently scroll day detail into view (guarded for jsdom/tests)
              setTimeout(() => {
                const el = dayDetailRef.current as any;
                el?.scrollIntoView?.({ behavior: "smooth", block: "start" });
              }, 0);
            }}
            selectedNarrativeBlockId={selectedNarrativeBlockId}
            onSelectNarrativeItem={(item: StoryboardItem) => {
              // Selecting a narrative item selects its day and highlights that block
              setSelectedDayIndex(item.dayIndex);
              setSelectedNarrativeBlockId(item.blockId);
              setSelectedBelief(null); // narrative selection clears belief panel
              setTimeout(() => {
                const el = dayDetailRef.current as any;
                el?.scrollIntoView?.({ behavior: "smooth", block: "start" });
              }, 0);
            }}
            onClickCameo={handleClickCameo}
          />
        );
      })()}

      {(() => {
        if (!episode || !selectedBelief) return null;
        // Compute belief text and factual summary from existing data
        let beliefText: string | null = null;
        try {
          const raw: any = (episode as any)._raw;
          const day = (Array.isArray(raw?.days) ? raw.days : []).find((d: any) => d?.day_index === selectedBelief.dayIndex);
          const a = day?.agents?.[selectedBelief.agentName];
          beliefText = typeof a?.attribution_cause === "string" ? a.attribution_cause : null;
        } catch {
          beliefText = null;
        }
        const dayVm = (episode.days || []).find((d) => d.index === selectedBelief.dayIndex) as any;
        const t = typeof dayVm?.tensionScore === "number" ? dayVm.tensionScore : 0;
        const inc = typeof dayVm?.totalIncidents === "number" ? dayVm.totalIncidents : 0;
        const sup = typeof dayVm?.supervisorActivity === "number" ? dayVm.supervisorActivity : 0;
        const what = `Tension ${t.toFixed(2)} • incidents ${inc} • supervisor ${sup.toFixed(0)}`;
        return (
          <AgentBeliefMiniPanel
            dayIndex={selectedBelief.dayIndex}
            agentName={selectedBelief.agentName}
            beliefText={beliefText}
            whatHappened={what}
          />
        );
      })()}

      <h2>Timeline</h2>
      <TimelineStrip
        days={episode.days}
        selectedIndex={selectedDayIndex}
        onSelect={(idx) => {
          setSelectedDayIndex(idx);
          setSelectedNarrativeBlockId(null); // timeline click highlights day; clear specific narrative selection
          setSelectedBelief(null); // timeline selection clears belief panel
          // Nudge storyboard to scroll the selected strip even if idx didn't change
          setScrollStoryboardToken((t) => t + 1);
        }}
        daySummaries={episode.daySummaries}
      />

      <h2>Day Detail</h2>
      <div ref={dayDetailRef} data-testid="day-detail-ref">
        <DayDetailPanel episode={episode} dayIndex={selectedDayIndex} />
      </div>

      <h2>Episode Agents Overview</h2>
      <EpisodeAgentsPanel episode={episode} />

      <h2>Episode Story</h2>
      <EpisodeStoryPanel story={episode.story} />
    </div>
  );
}
