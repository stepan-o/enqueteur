import { useEffect, useState } from "react";
import "./App.css";
import { getLatestEpisode } from "./api/episodes";
import type { EpisodeViewModel } from "./vm/episodeVm";
import { buildEpisodeView } from "./vm/episodeVm";

// -------------------------------
// Component
// -------------------------------
export default function App() {
    const [episode, setEpisode] = useState<EpisodeViewModel | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function load() {
            try {
                const raw = await getLatestEpisode();
                const vm = buildEpisodeView(raw);
                setEpisode(vm);
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
            <h1>Loopforge Stage Viewer</h1>
            <p>
                <strong>Episode:</strong> {episode.id}<br />
                <strong>Run:</strong> {episode.runId}<br />
                <strong>Days:</strong> {episode.days.length}<br />
                <strong>Stage Version:</strong> {episode.stageVersion}
            </p>

            <h2>Agents</h2>
            <ul>
                {episode.agents.map((agent) => (
                    <li key={agent.name}>
                        <strong>{agent.name}</strong> — start stress {agent.stressStart}, end stress {agent.stressEnd} (Δ {agent.stressDelta.toFixed(2)})
                    </li>
                ))}
            </ul>

            <h2>Day Tension Trend</h2>
            <ul>
                {episode.tensionTrend.map((v, i) => (
                    <li key={i}>
                        Day {i}: {v}
                    </li>
                ))}
            </ul>
        </div>
    );
}
