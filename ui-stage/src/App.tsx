import { useEffect, useState } from "react";
import "./App.css";

// -------------------------------
// Types matching StageEpisode v1
// -------------------------------
interface StageEpisode {
    stage_version: number;
    episode_id: string;
    run_id: string;
    episode_index: number;
    tension_trend: number[];
    days: StageDay[];
    agents: Record<string, StageAgentSummary>;
    narrative?: any;
}

interface StageDay {
    day_index: number;
    tension_score: number;
    total_incidents: number;
    perception_mode: string;
    supervisor_activity: number;
    agents: Record<string, StageAgentDayView>;
}

interface StageAgentSummary {
    stress_start: number;
    stress_end: number;
    guardrail_total: number;
    context_total: number;
}

interface StageAgentDayView {
    avg_stress: number;
    guardrail_count: number;
    context_count: number;
    emotional_read?: string | null;
    attribution_cause?: string | null;
}

// -------------------------------
// Component
// -------------------------------
export default function App() {
    const [episode, setEpisode] = useState<StageEpisode | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function load() {
            try {
                const res = await fetch("http://127.0.0.1:8000/episodes/latest");
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const data = await res.json();
                setEpisode(data);
            } catch (err: any) {
                setError(err.message);
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
