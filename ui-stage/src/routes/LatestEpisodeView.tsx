import { useEffect, useState } from "react";
import { getLatestEpisode } from "../api/episodes";
import type { EpisodeViewModel } from "../vm/episodeVm";
import { buildEpisodeView } from "../vm/episodeVm";
import EpisodeHeader from "../components/EpisodeHeader";
import TimelineStrip from "../components/TimelineStrip";
import DayDetailPanel from "../components/DayDetailPanel";
import EpisodeAgentsOverview from "../components/EpisodeAgentsOverview";

export default function LatestEpisodeView() {
  const [episode, setEpisode] = useState<EpisodeViewModel | null>(null);
  const [selectedDayIndex, setSelectedDayIndex] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const raw = await getLatestEpisode();
        const vm = buildEpisodeView(raw);
        setEpisode(vm);
        if (vm.days.length > 0) {
          setSelectedDayIndex(vm.days[0].index);
        } else {
          setSelectedDayIndex(0);
        }
      } catch (err: unknown) {
        if (err instanceof Error) setError(err.message);
        else setError("Unknown error");
      }
    }
    load();
  }, []);

  if (error) {
    return <div className="error">Error loading episode: {error}</div>;
  }

  if (!episode) {
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
