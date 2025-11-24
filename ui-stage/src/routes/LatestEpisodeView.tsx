import { useEffect, useState } from "react";
import type { EpisodeViewModel } from "../vm/episodeVm";
import EpisodeHeader from "../components/EpisodeHeader";
import TimelineStrip from "../components/TimelineStrip";
import DayDetailPanel from "../components/DayDetailPanel";
import EpisodeAgentsOverview from "../components/EpisodeAgentsOverview";
import { useEpisodeLoader } from "../hooks/useEpisodeLoader";

export default function LatestEpisodeView() {
  const { episode, error, isLoading } = useEpisodeLoader();
  const [selectedDayIndex, setSelectedDayIndex] = useState<number>(0);

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

  if (isLoading && !episode) {
    return <div className="loading">Loading latest StageEpisode…</div>;
  }

  return (
    <div>
      <EpisodeHeader episode={episode} />

      <h2>Timeline</h2>
      <TimelineStrip
        days={episode.days}
        selectedIndex={selectedDayIndex}
        onSelect={setSelectedDayIndex}
      />

      <h2>Day Detail</h2>
      <DayDetailPanel episode={episode} dayIndex={selectedDayIndex} />

      <h2>Episode Agents Overview</h2>
      <EpisodeAgentsOverview agents={episode.agents} />
    </div>
  );
}
