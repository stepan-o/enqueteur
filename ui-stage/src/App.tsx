import { useEffect, useState } from "react";
import "./App.css";
import type { StageEpisode } from "./types/stage";
import { getLatestEpisode } from "./api/episodes";

// -------------------------------
// Component
// -------------------------------
export default function App() {
    const [episode, setEpisode] = useState<StageEpisode | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function load() {
            try {
                const data = await getLatestEpisode();
                setEpisode(data);
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
                <strong>Episode:</strong> {episode.episode_id}<br />
                <strong>Run:</strong> {episode.run_id}<br />
                <strong>Days:</strong> {episode.days.length}<br />
                <strong>Stage Version:</strong> {episode.stage_version}
            </p>

            <h2>Agents</h2>
            <ul>
                {Object.entries(episode.agents).map(([agent, stats]) => (
                    <li key={agent}>
                        <strong>{agent}</strong> — start stress {stats.stress_start}, end stress{" "}
                        {stats.stress_end}
                    </li>
                ))}
            </ul>

            <h2>Day Tension Trend</h2>
            <ul>
                {episode.tension_trend.map((v, i) => (
                    <li key={i}>
                        Day {i}: {v}
                    </li>
                ))}
            </ul>
        </div>
    );
}
