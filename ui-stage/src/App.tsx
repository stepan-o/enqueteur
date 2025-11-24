import { useEffect, useState } from "react";
import "./App.css";
import { getLatestEpisode } from "./api/episodes";
import type { EpisodeViewModel } from "./vm/episodeVm";
import { buildEpisodeView } from "./vm/episodeVm";
import EpisodeHeader from "./components/EpisodeHeader";
import TimelineStrip from "./components/TimelineStrip";

// -------------------------------
// Component
// -------------------------------
export default function App() {
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
        <div className="App">
            <EpisodeHeader episode={episode} />

            <h2>Timeline</h2>
            <TimelineStrip
                days={episode.days}
                selectedIndex={selectedDayIndex}
                onSelect={setSelectedDayIndex}
            />

            <h2>Agents</h2>
            <ul>
                {episode.agents.map((agent) => (
                    <li key={agent.name}>
                        <strong>{agent.name}</strong> — start stress {agent.stressStart}, end stress {agent.stressEnd} (Δ {agent.stressDelta.toFixed(2)})
                    </li>
                ))}
            </ul>
        </div>
    );
}
