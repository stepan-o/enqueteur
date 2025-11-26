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
import { useRef } from "react";

export default function LatestEpisodeView() {
  const { episode, error, isLoading } = useEpisodeLoader();

  console.log("Render LatestEpisodeView", { episode, error, isLoading });

  const [selectedDayIndex, setSelectedDayIndex] = useState<number>(0);
  const dayDetailRef = useRef<HTMLDivElement | null>(null);
  const [selectedNarrativeBlockId, setSelectedNarrativeBlockId] = useState<string | null>(null);

  // Preserve initial selection logic: set to first day index when episode arrives
  useEffect(() => {
    if (episode) {
      if (episode.days.length > 0) {
        setSelectedDayIndex(episode.days[0].index);
      } else {
        setSelectedDayIndex(0);
      }
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
        return (
          <DayStoryboardList
            items={items}
            selectedDayIndex={selectedDayIndex}
            onSelectDay={(idx) => {
              setSelectedDayIndex(idx);
              setSelectedNarrativeBlockId(null); // day-level selection clears specific narrative selection
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
              setTimeout(() => {
                const el = dayDetailRef.current as any;
                el?.scrollIntoView?.({ behavior: "smooth", block: "start" });
              }, 0);
            }}
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
